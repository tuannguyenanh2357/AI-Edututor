from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Battle(models.Model):
    """Represents a PvP battle between two players."""

    STATUS_PENDING     = 'pending'       # Challenger sent, waiting for opponent
    STATUS_IN_PROGRESS = 'in_progress'   # Both players are playing
    STATUS_COMPLETED   = 'completed'     # Both submitted, winner decided
    STATUS_EXPIRED     = 'expired'       # Opponent never responded
    STATUS_CANCELLED   = 'cancelled'     # Challenger cancelled

    STATUS_CHOICES = [
        (STATUS_PENDING,     'Chờ đối thủ'),
        (STATUS_IN_PROGRESS, 'Đang diễn ra'),
        (STATUS_COMPLETED,   'Đã kết thúc'),
        (STATUS_EXPIRED,     'Hết hạn'),
        (STATUS_CANCELLED,   'Đã hủy'),
    ]

    challenger  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='battles_as_challenger')
    opponent    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='battles_as_opponent')
    grade_level = models.IntegerField(default=12)
    subject     = models.CharField(max_length=100, default='Toán học')
    # Stores list of DailyQuest IDs used in this battle
    question_ids = models.JSONField(default=list)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    winner      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='battles_won')
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField(null=True, blank=True)  # Auto-expire pending battles

    class Meta:
        db_table = 'battles'
        ordering = ['-created_at']
        verbose_name = 'Trận Đấu'
        verbose_name_plural = 'Trận Đấu'

    def __str__(self):
        return f"[{self.status}] {self.challenger} vs {self.opponent}"

    @property
    def is_draw(self):
        if self.status != self.STATUS_COMPLETED or self.winner is not None:
            return False
        return True


class BattleResult(models.Model):
    """Stores each player's performance in a battle."""

    battle        = models.ForeignKey(Battle, on_delete=models.CASCADE, related_name='results')
    player        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='battle_results')
    score         = models.IntegerField(default=0)      # Final calculated score
    correct_count = models.IntegerField(default=0)      # Number of correct answers
    total_time    = models.FloatField(default=0.0)      # Total seconds spent
    # JSON: { quest_id: { answer: "A", time_ms: 4200 } }
    answer_log    = models.JSONField(default=dict)
    submitted_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'battle_results'
        unique_together = ('battle', 'player')  # One result per player per battle
        verbose_name = 'Kết Quả Trận Đấu'
        verbose_name_plural = 'Kết Quả Trận Đấu'

    def __str__(self):
        return f"[Battle #{self.battle_id}] {self.player} — {self.score}pts"
