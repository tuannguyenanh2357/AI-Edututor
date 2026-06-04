"""
Challenge Views: Send and manage battle invitations.
"""
import random
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.quiz.models import Question
from ..models import Battle
from ..serializers import BattleDetailSerializer, BattleListSerializer
from ..services import redis_client

QUESTIONS_PER_BATTLE = 10
BATTLE_EXPIRY_HOURS  = 1
PENDING_EXPIRY_SECONDS = 20 # LoL Ready Check duration


class ChallengeSendView(APIView):
    """POST /api/battle/challenge/ — Send a battle invitation."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            opponent_id = request.data.get('opponent_id')
            grade_level = request.data.get('grade_level', request.user.grade_level)

            # --- Validation ---
            if not opponent_id:
                return Response({'error': 'opponent_id là bắt buộc.'}, status=400)

            if opponent_id == request.user.id:
                return Response({'error': 'Không thể tự thách đấu bản thân!'}, status=400)

            from apps.users.models import CustomUser
            try:
                opponent = CustomUser.objects.get(pk=opponent_id)
            except CustomUser.DoesNotExist:
                return Response({'error': 'Đối thủ không tồn tại.'}, status=404)

            # Expire any existing pending/in-progress battle between these two players to prevent soft-locks
            active_battles = Battle.objects.filter(
                challenger=request.user,
                opponent=opponent,
                status__in=[Battle.STATUS_PENDING, Battle.STATUS_IN_PROGRESS]
            )
            for active in active_battles:
                active.status = Battle.STATUS_EXPIRED
                active.save(update_fields=['status'])

            # --- Pick 10 random questions for this grade ---
            quests = list(
                Question.objects.filter(topic__lesson__chapter__subject__grade_level=grade_level).values_list('id', flat=True)
            )
            if len(quests) < QUESTIONS_PER_BATTLE:
                return Response(
                    {'error': f'Chưa đủ câu hỏi cho khối {grade_level}. Cần ít nhất {QUESTIONS_PER_BATTLE} câu.'},
                    status=400
                )

            selected_ids = random.sample(quests, QUESTIONS_PER_BATTLE)

            # --- Create Battle ---
            battle = Battle.objects.create(
                challenger=request.user,
                opponent=opponent,
                grade_level=grade_level,
                question_ids=selected_ids,
                status=Battle.STATUS_PENDING,
                expires_at=timezone.now() + timedelta(hours=BATTLE_EXPIRY_HOURS)
            )

            # Cache in Redis for fast polling
            try:
                redis_client.set_battle_state(battle.id, {
                    'status':        battle.status,
                    'challenger_id': request.user.id,
                    'opponent_id':   opponent.id,
                })
            except Exception as re:
                # Redis failure shouldn't stop the battle flow (falling back to DB polling)
                import logging
                logging.getLogger(__name__).warning(f"Redis set_battle_state failed: {re}")

            return Response(BattleDetailSerializer(battle).data, status=201)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc()) # Print to server console for debugging
            return Response({'error': f'Lỗi máy chủ: {str(e)}'}, status=500)


class PendingBattlesView(APIView):
    """GET /api/battle/pending/ — Get battles waiting for current user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Expire old battles first
        Battle.objects.filter(
            status=Battle.STATUS_PENDING,
            expires_at__lt=timezone.now()
        ).update(status=Battle.STATUS_EXPIRED)

        pending = Battle.objects.filter(
            opponent=request.user,
            status=Battle.STATUS_PENDING
        ).select_related('challenger')
        return Response(BattleListSerializer(pending, many=True).data)
