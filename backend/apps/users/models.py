from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('USER', 'User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER')
    full_name = models.CharField(max_length=255, blank=True)
    avatar_url = models.CharField(max_length=500, blank=True)
    bio = models.TextField(blank=True, default='')  # Tiểu sử người dùng
    date_of_birth = models.DateField(null=True, blank=True)  # Ngày sinh (dùng tính tuổi)
    
    # Gamification fields (Gamification 2.0 / PvP compatible)
    gems = models.IntegerField(default=0)
    total_xp = models.IntegerField(default=0) # Lifetime progress
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    
    # Legacy/Status fields
    rank = models.CharField(max_length=50, default='Beginner')
    grade_level = models.IntegerField(default=12)
    last_quest_date = models.DateField(null=True, blank=True)
    completed_quests = models.JSONField(default=dict, blank=True) # Changed default to dict to match json '{}'

    # AI & Chat Preferences
    ai_preferences = models.TextField(blank=True, default="")
    is_global_history_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'users'

    def update_rank(self, commit=True):
        """Calculates and updates the rank string based on total_xp."""
        if self.total_xp >= 10000: self.rank = "Huyền Thoại"
        elif self.total_xp >= 5000: self.rank = "Đại Hiệp"
        elif self.total_xp >= 2000: self.rank = "Chiến Binh"
        elif self.total_xp >= 500: self.rank = "Học Giả"
        else: self.rank = "Tập Sự"
        
        if commit:
            self.save(update_fields=['rank'])

    def __str__(self):
        return f"{self.username} - {self.role}"

    def save(self, *args, **kwargs):
        # Đồng bộ role field với is_superuser/is_staff của Django
        if self.is_superuser or self.is_staff:
            self.role = 'ADMIN'
        super().save(*args, **kwargs)

class UserStat(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='stats')
    total_xp = models.IntegerField(default=0)
    lessons_completed = models.IntegerField(default=0)
    perfect_quizzes = models.IntegerField(default=0)
    pvp_wins = models.IntegerField(default=0)
    pvp_games_played = models.IntegerField(default=0)
    max_win_streak = models.IntegerField(default=0)
    tower_floor_reached = models.IntegerField(default=0)
    chat_messages_count = models.IntegerField(default=0)
    ai_explanations_requested = models.IntegerField(default=0)
    gems_earned = models.IntegerField(default=0)
    login_streak = models.IntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)
    total_sessions = models.IntegerField(default=0)
    last_active_at = models.DateTimeField(null=True, blank=True)
    current_subject_id = models.BigIntegerField(null=True, blank=True)
    current_chapter_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'user_stats'

class LearningPath(models.Model):
    """Lộ trình học tập cá nhân hóa — 1 user có 1 path per chương (chapter-test là luồng chính)."""
    STATUS_CHOICES = [
        ('ACTIVE', 'Đang học'),
        ('COMPLETED', 'Đã hoàn thành'),
        ('PENDING', 'Chờ AI phân tích'),
        ('LOCKED', 'Chưa mở khóa'),
    ]
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='learning_paths'
    )
    subject = models.ForeignKey(
        'subjects.Subject', on_delete=models.CASCADE, related_name='learning_paths', null=True, blank=True
    )
    # Chapter-based path: 1 lộ trình riêng cho mỗi chương
    chapter = models.ForeignKey(
        'curriculum.Chapter', on_delete=models.CASCADE, related_name='learning_paths', null=True, blank=True
    )
    pre_test_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Điểm đánh giá đầu vào (%)"
    )
    strategy = models.CharField(
        max_length=20,
        choices=[('foundation', 'Nền tảng'), ('standard', 'Tiêu chuẩn'), ('advanced', 'Nâng cao')],
        default='standard',
        help_text="Chiến lược học do AI chọn"
    )
    ai_feedback = models.TextField(
        blank=True, default='',
        help_text="Nhận xét cá nhân hóa từ Gemini"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    # Kết quả bài kiểm tra đầu ra (Post-test) sau khi học xong lộ trình
    post_test_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Điểm bài kiểm tra cuối chương (%)"
    )
    post_test_ai_feedback = models.TextField(
        blank=True, default='',
        help_text="Nhận xét AI so sánh trước/sau khi học"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'learning_paths'
        # Mỗi user chỉ có 1 lộ trình per chương (chapter-based)
        # subject + chapter có thể null để backward-compatible
        ordering = ['-created_at']

    def __str__(self):
        if self.chapter:
            return f"{self.user.username} - Chương: {self.chapter.title} ({self.status})"
        return f"{self.user.username} - {self.subject.name if self.subject else 'N/A'} ({self.status})"

class LearningPathItem(models.Model):
    """Từng bước cụ thể trong lộ trình học (Lesson hoặc Quiz)."""
    ITEM_TYPES = [
        ('LESSON', 'Bài học lớn'),
        ('TOPIC', 'Mục kiến thức'),
        ('QUIZ', 'Kiểm tra'),
    ]
    learning_path = models.ForeignKey(
        LearningPath, on_delete=models.CASCADE, related_name='items'
    )
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    lesson = models.ForeignKey(
        'curriculum.Lesson', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='path_items'
    )
    topic = models.ForeignKey(
        'curriculum.Topic', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='path_items',
        help_text="Mục nhỏ cụ thể cần học"
    )
    quiz = models.ForeignKey(
        'quiz.Quiz', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='path_items'
    )
    order_num = models.IntegerField(default=0)
    is_unlocked = models.BooleanField(default=False)

    class Meta:
        db_table = 'learning_path_items'
        ordering = ['order_num']

    def __str__(self):
        label = self.lesson.title if self.lesson else (self.quiz.title if self.quiz else '?')
        return f"[{self.item_type}] {label} (order={self.order_num})"

class LearningProgress(models.Model):
    """Tiến trình của user cho từng item trong lộ trình."""
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Chưa bắt đầu'),
        ('IN_PROGRESS', 'Đang học'),
        ('COMPLETED', 'Hoàn thành'),
    ]
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='learning_progress'
    )
    learning_path_item = models.ForeignKey(
        LearningPathItem, on_delete=models.CASCADE, related_name='progress_records'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Điểm quiz nếu item là QUIZ"
    )
    mastery_level = models.CharField(
        max_length=20,
        choices=[('RED', 'Yếu'), ('YELLOW', 'Cần cố gắng'), ('GREEN', 'Thành thạo')],
        default='RED',
        help_text="Mức độ thông thạo theo hệ thống Đèn giao thông"
    )
    error_tags = models.JSONField(
        default=list, blank=True,
        help_text="Lưu các tag lỗi sai để AI phân tích nguyên nhân (ví dụ: 'ẩu', 'hổng-kiến-thức')"
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'learning_progress'
        unique_together = ('user', 'learning_path_item')

    def __str__(self):
        return f"{self.user.username} - Item#{self.learning_path_item_id} ({self.status})"
