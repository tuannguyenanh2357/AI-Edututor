from django.db import transaction
from django.db.models import F
from ..models import Battle, BattleResult
from . import redis_client, scoring

def finalize_battle(battle: Battle) -> dict:
    """
    Compare results, set winner, award rewards/penalties, and return final outcome.
    Can be called from submission view or status polling (self-healing).
    """
    with transaction.atomic():
        # Lock the battle record to prevent race conditions
        battle = Battle.objects.select_for_update().get(pk=battle.id)
        
        if battle.status == Battle.STATUS_COMPLETED:
            # Already done, just return result map for response
            results = list(battle.results.select_related('player').all())
            result_map = {r.player_id: r for r in results}
            return {
                'status': 'completed',
                'winner': battle.winner.username if battle.winner else None,
                'is_draw': battle.winner is None,
                'results': result_map
            }

        results = list(battle.results.select_related('player').all())
        if len(results) < 2:
            return {'status': 'submitted', 'message': 'Đang chờ đối thủ...'}

        result_map = {r.player_id: r for r in results}
        r_challenger = result_map.get(battle.challenger_id)
        r_opponent   = result_map.get(battle.opponent_id)

        winner_result = scoring.determine_winner(r_challenger, r_opponent)
        
        battle.status = Battle.STATUS_COMPLETED
        battle.winner = winner_result.player if winner_result else None
        battle.save(update_fields=['status', 'winner'])

        # ─────────────────────────────────────────────────
        # REWARDS & PENALTIES
        # ─────────────────────────────────────────────────
        winner = battle.winner
        
        if winner:
            loser = battle.opponent if winner == battle.challenger else battle.challenger
            w_result = result_map.get(winner.id)
            
            # Winner: +Score as XP, +10 Gems
            winner.total_xp += w_result.score
            winner.gems += 10
            winner.update_rank(commit=False)
            winner.save(update_fields=['total_xp', 'gems', 'rank'])
            
            # Loser: -50 XP (clamped at 0)
            loser.total_xp = max(0, loser.total_xp - 50)
            loser.update_rank(commit=False)
            loser.save(update_fields=['total_xp', 'rank'])
        else:
            # Draw: Each gets 50% score as XP
            for res in results:
                p = res.player
                p.total_xp += int(res.score * 0.5)
                p.update_rank(commit=False)
                p.save(update_fields=['total_xp', 'rank'])

        # Cleanup Redis
        redis_client.cleanup_battle(battle.id, battle.challenger_id, battle.opponent_id)

    return {
        'status':    'completed',
        'winner':    battle.winner.username if battle.winner else None,
        'is_draw':   battle.winner is None,
        'results':   result_map
    }
