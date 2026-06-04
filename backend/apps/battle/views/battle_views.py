"""
Battle Views: Accept challenge and submit answers.
"""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.quiz.models import Question
from ..models import Battle, BattleResult
from ..serializers import BattleDetailSerializer, SubmitAnswersSerializer
from ..services import redis_client, scoring, battle_logic


class BattleDetailView(APIView):
    """
    GET  /api/battle/<id>/  — Get battle info + questions to render UI.
    POST /api/battle/<id>/accept/ — Opponent accepts → status = in_progress.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, battle_id):
        battle = get_object_or_404(Battle, pk=battle_id)

        # Only participants can view
        if request.user not in [battle.challenger, battle.opponent]:
            return Response({'error': 'Bạn không phải thành viên của trận đấu này.'}, status=403)

        # Attach question data for the frontend
        serialized = BattleDetailSerializer(battle).data
        
        # Lấy từ bảng Question thay vì DailyQuest
        questions = Question.objects.filter(pk__in=battle.question_ids).prefetch_related('answers')
        
        quest_map = {}
        for q in questions:
            opts_dict = {}
            correct_ans = "A"
            for i, ans in enumerate(q.answers.all()):
                label = chr(65 + i)
                opts_dict[label] = ans.answer_text
                if ans.is_correct:
                    correct_ans = label
            
            quest_map[q.id] = {
                'id': q.id,
                'question_text': q.question_text,
                'options': opts_dict,
                'grade_level': battle.grade_level, # Lấy grade từ battle cho nhanh
                'correct_answer': correct_ans
            }

        # Return in the same order as question_ids
        serialized['questions'] = [quest_map[qid] for qid in battle.question_ids if qid in quest_map]

        return Response(serialized)


class BattleAcceptView(APIView):
    """POST /api/battle/<int:battle_id>/accept/ — Opponent accepts the challenge."""
    permission_classes = [IsAuthenticated]

    def post(self, request, battle_id):
        from django.db import transaction
        with transaction.atomic():
            battle = Battle.objects.select_for_update().get(pk=battle_id, opponent=request.user)
            
            if battle.status != Battle.STATUS_PENDING:
                return Response({'error': 'Trận đấu không còn ở trạng thái chờ.'}, status=400)
            
            battle.status = Battle.STATUS_IN_PROGRESS
            # Set fresh expiry for active battle (30 mins)
            from django.utils import timezone
            from datetime import timedelta
            battle.expires_at = timezone.now() + timedelta(minutes=30)
            battle.save(update_fields=['status', 'expires_at'])

            # Update Redis for fast synchronization
            redis_client.set_battle_state(battle.id, {
                'status':        battle.status,
                'challenger_id': battle.challenger_id,
                'opponent_id':   battle.opponent_id,
            })

            return Response({'status': 'accepted', 'battle_id': battle.id})


class BattleDeclineView(APIView):
    """POST /api/battle/<int:battle_id>/decline/ — Challenger or Opponent cancels the challenge."""
    permission_classes = [IsAuthenticated]

    def post(self, request, battle_id):
        from django.db.models import Q
        battle = get_object_or_404(Battle, Q(pk=battle_id) & (Q(challenger=request.user) | Q(opponent=request.user)))
        
        if battle.status != Battle.STATUS_PENDING:
            return Response({'error': 'Không thể hủy trận đấu này.'}, status=400)
        
        battle.status = Battle.STATUS_CANCELLED
        battle.save(update_fields=['status'])

        # Notify participants via Redis
        redis_client.set_battle_state(battle.id, {'status': battle.status})

        return Response({'status': 'declined'})


class BattleSubmitView(APIView):
    """POST /api/battle/<id>/submit/ — Player submits their answers."""
    permission_classes = [IsAuthenticated]

    def post(self, request, battle_id):
        battle = get_object_or_404(Battle, pk=battle_id)
        user   = request.user

        # Only participants can submit
        if user not in [battle.challenger, battle.opponent]:
            return Response({'error': 'Bạn không phải thành viên của trận đấu này.'}, status=403)

        if battle.status not in [Battle.STATUS_PENDING, Battle.STATUS_IN_PROGRESS]:
            return Response({'error': 'Trận đấu này đã kết thúc.'}, status=400)

        # Prevent double submission
        if BattleResult.objects.filter(battle=battle, player=user).exists():
            return Response({'error': 'Bạn đã nộp bài cho trận đấu này rồi.'}, status=400)

        # Validate payload
        ser = SubmitAnswersSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        answer_log = ser.validated_data['answer_log']

        # Get correct answers from DB
        questions = Question.objects.filter(pk__in=battle.question_ids).prefetch_related('answers')
        correct_answers = {}
        for q in questions:
            for j, ans in enumerate(q.answers.all()):
                if ans.is_correct:
                    correct_answers[str(q.id)] = chr(65 + j)
                    break

        # Calculate score
        result_data = scoring.calculate_score(answer_log, correct_answers)

        # Save result
        BattleResult.objects.create(
            battle=battle,
            player=user,
            score=result_data['score'],
            correct_count=result_data['correct_count'],
            total_time=result_data['total_time'],
            answer_log=answer_log,
        )

        # Mark as submitted in Redis
        redis_client.mark_player_submitted(battle.id, user.id)

        # Check if BOTH players have submitted → finalize
        # [FIX] Add DB-level fallback (results.count()) in case Redis is unavailable or out of sync
        if redis_client.both_players_submitted(battle.id, battle.challenger_id, battle.opponent_id) or battle.results.count() >= 2:
            outcome = battle_logic.finalize_battle(battle)
            if outcome['status'] == 'completed':
                results = outcome['results']
                return Response({
                    'status':    'completed',
                    'winner':    outcome['winner'],
                    'is_draw':   outcome['is_draw'],
                    'your_score':    results.get(user.id).score if results.get(user.id) else 0,
                    'opponent_score': next(r.score for r in results.values() if r.player_id != user.id),
                })

        return Response({
            'status': 'submitted',
            'message': 'Đã nộp bài! Đang chờ đối thủ hoàn thành...',
            'your_score': result_data['score'],
        })
