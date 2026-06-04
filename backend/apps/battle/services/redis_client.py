"""
Redis client for managing real-time battle state.

Uses Redis as a fast, temporary store for:
- Tracking which players have submitted results
- Caching current battle state to avoid repeated DB queries
- Auto-expiring stale battles (TTL-based)

Falls back gracefully if Redis is unavailable (uses DB only).
"""

import json
import logging

logger = logging.getLogger(__name__)

BATTLE_TTL_SECONDS = 60 * 30  # 30 minutes


def _get_redis():
    """Lazily import and return Redis client. Returns None if unavailable."""
    try:
        import redis
        client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"[Redis] Unavailable, falling back to DB-only mode: {e}")
        return None


# ──────────────────────────────────────────────
# KEY HELPERS
# ──────────────────────────────────────────────

def _battle_key(battle_id: int) -> str:
    return f"battle:{battle_id}:state"

def _submitted_key(battle_id: int, player_id: int) -> str:
    return f"battle:{battle_id}:submitted:{player_id}"


# ──────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────

def set_battle_state(battle_id: int, state: dict) -> None:
    """Cache battle state dict in Redis with TTL."""
    r = _get_redis()
    if r:
        r.setex(_battle_key(battle_id), BATTLE_TTL_SECONDS, json.dumps(state))


def get_battle_state(battle_id: int) -> dict | None:
    """Retrieve cached battle state. Returns None if not found."""
    r = _get_redis()
    if r:
        raw = r.get(_battle_key(battle_id))
        if raw:
            return json.loads(raw)
    return None


def mark_player_submitted(battle_id: int, player_id: int) -> None:
    """Record that a player has submitted their answers."""
    r = _get_redis()
    if r:
        r.setex(_submitted_key(battle_id, player_id), BATTLE_TTL_SECONDS, '1')


def has_player_submitted(battle_id: int, player_id: int) -> bool:
    """Check if a player has already submitted."""
    r = _get_redis()
    if r:
        return r.exists(_submitted_key(battle_id, player_id)) == 1
    return False


def both_players_submitted(battle_id: int, challenger_id: int, opponent_id: int) -> bool:
    """Check if both players have submitted their answers."""
    return (
        has_player_submitted(battle_id, challenger_id) and
        has_player_submitted(battle_id, opponent_id)
    )


def cleanup_battle(battle_id: int, challenger_id: int, opponent_id: int) -> None:
    """Remove all Redis keys for a completed battle."""
    r = _get_redis()
    if r:
        r.delete(
            _battle_key(battle_id),
            _submitted_key(battle_id, challenger_id),
            _submitted_key(battle_id, opponent_id),
        )
