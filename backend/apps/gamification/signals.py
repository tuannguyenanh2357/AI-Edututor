from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.users.models import UserStat
from .models import Badge, UserBadge

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_stat(sender, instance, created, **kwargs):
    if created:
        UserStat.objects.get_or_create(user=instance)

@receiver(post_save, sender=UserStat)
def check_badges(sender, instance, **kwargs):
    """
    Kiểm tra và tặng huy hiệu mỗi khi chỉ số (UserStat) thay đổi.
    """
    user = instance.user
    all_badges = Badge.objects.all()
    
    # Lấy danh sách huy hiệu user đã có để tránh tặng trùng
    earned_badge_ids = UserBadge.objects.filter(user=user).values_list('badge_id', flat=True)
    
    newly_earned = []
    
    for badge in all_badges:
        if badge.id in earned_badge_ids:
            continue
            
        # Lấy giá trị thực tế từ UserStat dựa trên criteria_type
        current_value = getattr(instance, badge.criteria_type, 0)
        
        if current_value >= badge.requirement_value:
            # Chúc mừng! Bạn đã đạt huy hiệu mới
            UserBadge.objects.create(user=user, badge=badge)
            newly_earned.append(badge.name)
            
    if newly_earned:
        print(f"User {user.username} vừa đạt các huy hiệu: {', '.join(newly_earned)}")
