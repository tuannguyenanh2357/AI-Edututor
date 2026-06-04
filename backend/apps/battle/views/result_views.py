"""
Result Views: Battle history and status polling.
"""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Battle
from ..serializers import BattleListSerializer, BattleDetailSerializer
from ..services import battle_logic


class BattleStatusView(APIView):
    """
    GET /api/battle/<id>/status/ — Poll for battle completion.
    Frontend polls this every 3 seconds to check if opponent submitted.
    Lightweight: returns only status + winner, no question data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, battle_id):
        battle = get_object_or_404(Battle, pk=battle_id)

        if request.user not in [battle.challenger, battle.opponent]:
            return Response({'error': 'Không có quyền truy cập.'}, status=403)

        # [SELF-HEALING] If stuck in_progress but has 2 results, finalize now
        if battle.status == Battle.STATUS_IN_PROGRESS and battle.results.count() >= 2:
            battle_logic.finalize_battle(battle)
            battle.refresh_from_db()

        data = {
            'status':     battle.status,
            'winner':     battle.winner.username if battle.winner else None,
            'is_draw':    battle.is_draw,
            'result_count': battle.results.count(),
        }

        # Include scores when completed
        if battle.status == Battle.STATUS_COMPLETED:
            results = {r.player_id: r for r in battle.results.all()}
            user_result     = results.get(request.user.id)
            opponent_id     = battle.opponent_id if request.user == battle.challenger else battle.challenger_id
            opponent_result = results.get(opponent_id)

            data['your_score']      = user_result.score if user_result else 0
            data['opponent_score']  = opponent_result.score if opponent_result else 0
            data['your_correct']    = user_result.correct_count if user_result else 0
            data['opponent_correct']= opponent_result.correct_count if opponent_result else 0

        return Response(data)


class BattleHistoryView(APIView):
    """GET /api/battle/history/ — Current user's battle history."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        battles = Battle.objects.filter(
            challenger=request.user
        ) | Battle.objects.filter(
            opponent=request.user
        )
        battles = battles.exclude(
            status__in=[Battle.STATUS_PENDING]
        ).select_related('challenger', 'opponent', 'winner').prefetch_related('results__player').order_by('-created_at')

        return Response(BattleListSerializer(battles, many=True).data)
