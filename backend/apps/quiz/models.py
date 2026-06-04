from django.db import models
from django.conf import settings
from apps.subjects.models import Subject, SubjectDocument


class Quiz(models.Model):
    QUIZ_TYPES = [
        ('PRE_TEST', 'Pre-Test (Đầu vào)'),
        ('POST_TEST', 'Post-Test (Vượt ải)'),
        ('PRACTICE', 'Practice (Luyện tập AI)'),
        ('CHAPTER_TEST', 'Chapter Test (Đánh giá đầu vào theo Chương)'),
    ]
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    related_document = models.ForeignKey(
        SubjectDocument, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='quizzes',
        help_text="Tài liệu/trang sách liên kết (Dành cho Post-test và Practice)"
    )
    quiz_type = models.CharField(max_length=20, choices=QUIZ_TYPES, default='PRACTICE')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    difficulty = models.CharField(max_length=20, blank=True, null=True)
    passing_score = models.IntegerField(default=70, help_text="Điểm sàn để vượt qua (%)")
    # Lưu chapter_title để evaluator biết câu thuộc chương nào
    chapter_coverage = models.JSONField(
        default=list, blank=True,
        help_text="Danh sách chapter_title mà quiz này bao phủ"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quizzes'

    def __str__(self):
        return f"[{self.quiz_type}] {self.title}"


class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Trắc nghiệm 1 đáp án'),
        ('TRUE_FALSE', 'Đúng/Sai'),
    ]
    LEVEL_CHOICES = [
        (1, 'Nhận biết (Remember)'),
        (2, 'Thông hiểu (Understand)'),
        (3, 'Vận dụng (Apply)'),
        (4, 'Phân tích (Analyze)'),
        (5, 'Đánh giá (Evaluate)'),
        (6, 'Sáng tạo (Create)'),
    ]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    
    # Liên kết phân cấp: trỏ trực tiếp đến Topic (Phần nhỏ của bài học)
    topic = models.ForeignKey(
        'curriculum.Topic', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='questions',
        help_text="Liên kết câu hỏi với mục kiến thức cụ thể"
    )
    
    difficulty_level = models.IntegerField(
        choices=LEVEL_CHOICES, 
        default=1,
        help_text="Cấp độ nhận thức theo thang đo Bloom (1-6)"
    )

    bloom_level = models.IntegerField(default=1, help_text="Cấp độ Bloom (1-6)")
    difficulty_score = models.FloatField(default=1.0, help_text="Độ khó thực tế (0.0 - 10.0)")
    
    is_input_test = models.BooleanField(default=False, help_text="Sử dụng cho bài kiểm tra đầu vào/phân loại")
    is_boss_question = models.BooleanField(default=False, help_text="Câu hỏi chốt hạ để vượt tầng tháp")
    battle_eligible = models.BooleanField(default=False, help_text="Câu hỏi đủ điều kiện sử dụng trong Đấu trường")
    verified_answer = models.BooleanField(default=False, help_text="Câu hỏi đã được xác minh tính đúng đắn (qua thực tế làm bài)")

    question_text = models.TextField()
    question_type = models.CharField(max_length=50, default='MCQ', choices=QUESTION_TYPES)
    
    # --- PHÂN TÁCH TRƯỜNG DỮ LIỆU RÕ RÀNG (FLOW MỚI) ---
    part_title = models.CharField(max_length=255, blank=True, null=True, help_text="Tên Phần (Ví dụ: Phần 1)")
    chapter_title = models.CharField(max_length=255, blank=True, null=True, help_text="Tên Chương hoặc Tên Chủ đề")
    chapter_type = models.CharField(
        max_length=20, 
        choices=[('CHAPTER', 'Chương'), ('THEME', 'Chủ đề')], 
        null=True, blank=True,
        help_text="Phân loại: Chương (Tự nhiên) hoặc Chủ đề (Xã hội)"
    )
    lesson_title = models.CharField(max_length=255, blank=True, null=True, help_text="Tên bài học")
    lesson_number = models.CharField(max_length=50, blank=True, null=True, help_text="Số thứ tự bài học (ví dụ: Bài 1)")
    subject_name = models.CharField(max_length=100, blank=True, null=True, help_text="Tên môn học")
    grade_level = models.IntegerField(blank=True, null=True, help_text="Khối lớp (10, 11, 12)")
    
    explanation = models.TextField(blank=True, null=True, help_text="Giải thích đáp án đúng")
    order_num = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'questions'

    def save(self, *args, **kwargs):
        # Tự động đồng bộ metadata từ Topic -> Question khi lưu
        if self.topic:
            try:
                lesson = self.topic.lesson
                chapter = lesson.chapter
                subj = chapter.subject
                
                # Cập nhật metadata từ cây curriculum
                if not self.lesson_title: self.lesson_title = lesson.title
                if not self.lesson_number: self.lesson_number = lesson.lesson_number
                if not self.chapter_title: self.chapter_title = chapter.title
                if not self.chapter_type: self.chapter_type = chapter.chapter_type
                if not self.subject_name: self.subject_name = subj.name
                if self.grade_level is None: self.grade_level = subj.grade_level

                if chapter.part and not self.part_title:
                    self.part_title = chapter.part.title
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        prefix = f"[{self.get_difficulty_level_display()}]"
        return f"{prefix} Q{self.order_num}: {self.question_text[:60]}"


class Answer(models.Model):
    """Đáp án cho mỗi câu hỏi (A, B, C, D)."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order_num = models.IntegerField(default=0)

    class Meta:
        db_table = 'answers'
        ordering = ['order_num']

    def __str__(self):
        correct_tag = " ✓" if self.is_correct else ""
        return f"Q{self.question_id} - {self.answer_text[:40]}{correct_tag}"


class QuizSubmission(models.Model):
    """Kết quả nộp bài của người dùng."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_submissions'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='submissions')
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # {"question_id": answer_id, ...} — lưu câu trả lời của user
    answers_data = models.JSONField(default=dict, blank=True)
    # Danh sách chapter_title mà user trả lời sai (để evaluator dùng)
    wrong_chapters = models.JSONField(default=list, blank=True)
    # Báo cáo năng lực chi tiết theo Bloom {"bloom_1": 80, "bloom_2": 60, ...}
    bloom_analysis = models.JSONField(default=dict, blank=True)
    passed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quiz_submissions'

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.score}%"
