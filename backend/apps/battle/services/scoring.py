"""
Scoring engine for PvP battles.

Formula:
  base_score   = correct_answers × 100
  speed_bonus  = Σ max(0, TIME_LIMIT - time_per_question_s) × 5
  final_score  = base_score + speed_bonus

Tiebreaker: If scores are equal, the player with less total_time wins.
"""

TIME_LIMIT_PER_QUESTION = 15  # seconds
BASE_POINTS_PER_CORRECT = 100
SPEED_BONUS_MULTIPLIER  = 5


def calculate_score(answer_log: dict, correct_answers: dict) -> dict:
    """
    Calculate a player's final score from their answer log.

    Args:
        answer_log: { str(quest_id): { "answer": "A", "time_ms": 4200 } }
        correct_answers: { str(quest_id): "A" }

    Returns:
        {
            "score": int,
            "correct_count": int,
            "total_time": float  (seconds)
        }
    """
    correct_count = 0
    speed_bonus   = 0
    total_time_ms = 0

    for quest_id, log in answer_log.items():
        chosen   = log.get('answer', '')
        time_ms  = log.get('time_ms', TIME_LIMIT_PER_QUESTION * 1000)
        time_s   = time_ms / 1000

        total_time_ms += time_ms

        if chosen == correct_answers.get(quest_id):
            correct_count += 1
            remaining = max(0, TIME_LIMIT_PER_QUESTION - time_s)
            speed_bonus += remaining * SPEED_BONUS_MULTIPLIER

    base_score  = correct_count * BASE_POINTS_PER_CORRECT
    final_score = int(base_score + speed_bonus)

    return {
        'score':         final_score,
        'correct_count': correct_count,
        'total_time':    round(total_time_ms / 1000, 2),
    }


def determine_winner(result_a, result_b):
    """
    Compare two BattleResult objects and return the winner.

    Args:
        result_a, result_b: BattleResult instances

    Returns:
        winner (BattleResult) or None if draw
    """
    if result_a.score > result_b.score:
        return result_a
    if result_b.score > result_a.score:
        return result_b
    # Tiebreaker: faster total time wins
    if result_a.total_time < result_b.total_time:
        return result_a
    if result_b.total_time < result_a.total_time:
        return result_b
    return None  # True draw
