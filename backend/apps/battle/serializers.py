from rest_framework import serializers
from .models import Battle, BattleResult
from apps.users.models import CustomUser


class PlayerSerializer(serializers.ModelSerializer):
    """Lightweight user info for battle display."""
    class Meta:
        model  = CustomUser
        fields = ['id', 'username', 'rank', 'total_xp', 'grade_level']


class BattleResultSerializer(serializers.ModelSerializer):
    player = PlayerSerializer(read_only=True)

    class Meta:
        model  = BattleResult
        fields = ['player', 'score', 'correct_count', 'total_time', 'submitted_at']


class BattleListSerializer(serializers.ModelSerializer):
    """Used in lobby & history list — no question data."""
    challenger = PlayerSerializer(read_only=True)
    opponent   = PlayerSerializer(read_only=True)
    winner     = PlayerSerializer(read_only=True)
    results    = BattleResultSerializer(many=True, read_only=True)

    class Meta:
        model  = Battle
        fields = [
            'id', 'challenger', 'opponent', 'grade_level',
            'status', 'winner', 'results', 'created_at', 'expires_at'
        ]


class BattleDetailSerializer(serializers.ModelSerializer):
    """
    Used when a player opens a battle to play.
    Includes question_ids but NOT correct answers (security).
    Frontend fetches questions separately via gamification API.
    """
    challenger = PlayerSerializer(read_only=True)
    opponent   = PlayerSerializer(read_only=True)

    class Meta:
        model  = Battle
        fields = [
            'id', 'challenger', 'opponent', 'grade_level',
            'question_ids', 'status', 'created_at', 'expires_at'
        ]


class SubmitAnswersSerializer(serializers.Serializer):
    """Validates incoming answer submission from frontend."""
    # { "123": { "answer": "A", "time_ms": 4200 }, ... }
    answer_log = serializers.DictField(
        child=serializers.DictField(),
        help_text="Dict of quest_id → { answer, time_ms }"
    )

    def validate_answer_log(self, value):
        for q_id, data in value.items():
            if 'answer' not in data or 'time_ms' not in data:
                raise serializers.ValidationError(f"Dữ liệu câu hỏi {q_id} thiếu trường 'answer' hoặc 'time_ms'.")
            if not isinstance(data.get('time_ms'), (int, float)):
                raise serializers.ValidationError(f"Thời gian câu hỏi {q_id} phải là con số.")
        return value
