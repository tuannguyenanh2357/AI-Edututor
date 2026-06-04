from django.db import models
from django.conf import settings
from apps.subjects.models import Subject


class Badge(models.Model):
    CATEGORIES = [
        ('LEARNING', 'Học tập'),
        ('ARENA', 'Đấu trường'),
        ('SOCIAL', 'Xã hội'),
        ('CONSISTENCY', 'Chuyên cần'),
        ('AI', 'Trí tuệ nhân tạo'),
    ]
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, default='GENERIC_BADGE')
    description = models.TextField()
    icon_url = models.CharField(max_length=255, blank=True, null=True) 
    category = models.CharField(max_length=20, choices=CATEGORIES, default='LEARNING')
    
    # Logic điều kiện
    criteria_type = models.CharField(max_length=50, default='generic', help_text="Ví dụ: lessons_completed, pvp_wins, chat_count")
    requirement_value = models.IntegerField(default=0)

    class Meta:
        db_table = 'badges'

    def __str__(self):
        return f"[{self.category}] {self.name}"

class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_badges'
        unique_together = ('user', 'badge')

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"

class StoreItem(models.Model):
    ITEM_TYPES = [
        ('STREAK_FREEZE', 'Băng nén chuỗi'),
        ('XP_BOOST', 'Tăng tốc XP'),
        ('THEME', 'Giao diện đặc biệt'),
        ('HINT', 'Gợi ý bài tập'),
        ('OTHER', 'Khác'),
    ]
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price_gems = models.IntegerField(default=50)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='OTHER')
    icon_name = models.CharField(max_length=50, default='fas fa-cube') # FontAwesome icon name
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'store_items'

    def __str__(self):
        return self.name

class Inventory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(StoreItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    acquired_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False) # For one-time use items like Streak Freeze

    class Meta:
        db_table = 'inventories'
        verbose_name_plural = "Inventories"

    def __str__(self):
        return f"{self.user.username} - {self.item.name} ({self.quantity})"
