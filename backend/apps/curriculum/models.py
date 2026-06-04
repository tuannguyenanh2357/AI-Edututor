from django.db import models
from apps.subjects.models import Subject


class Part(models.Model):
    """
    Cấp cao nhất - Phần/Khối (ví dụ: 'Giáo dục Kinh tế', 'Phần 1').
    Tồn tại trong sách GDCD, Địa lý... Có thể không có ở một số sách.
    """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='parts')
    title = models.CharField(max_length=255, help_text="Tên phần (ví dụ: Giáo dục Kinh tế)")
    order_num = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'parts'
        ordering = ['order_num']

    def __str__(self):
        return f"[{self.subject.name}] Phần: {self.title}"


class Chapter(models.Model):
    """
    Chương HOẶC Chủ đề (cấp 2) - phân biệt bằng chapter_type.

    Mỗi sách có thể dùng cách gọi khác nhau:
    - Toán, Lý, Hóa, Sinh → dùng "Chương" → chapter_type=CHAPTER, ten_chuong được điền
    - Vật Lý (bộ mới), GDCD, Lịch sử, Địa lý → dùng "Chủ đề" → chapter_type=THEME, ten_chu_de được điền

    Trường 'title' luôn chứa tên hiển thị (bằng ten_chuong hoặc ten_chu_de).
    """
    CHAPTER_TYPE_CHOICES = [
        ('CHAPTER', 'Chương'),
        ('THEME', 'Chủ đề'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')
    part = models.ForeignKey(
        Part, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='chapters',
        help_text="Phần/Khối chứa Chương này (nếu có)"
    )
    chapter_type = models.CharField(
        max_length=10, choices=CHAPTER_TYPE_CHOICES, default='CHAPTER',
        help_text="CHAPTER = Chương (Toán/Lý/Hóa), THEME = Chủ đề (Lý mới/GDCD/LS/ĐL)"
    )

    # ── Cột riêng biệt: lưu đúng loại vào đúng cột ────────────────────────────
    ten_chuong = models.CharField(
        max_length=512, blank=True, null=True,
        db_column='ten_chuong',
        help_text="Tên Chương - chỉ điền khi chapter_type=CHAPTER (ví dụ: Chương 1: Mệnh đề)"
    )
    ten_chu_de = models.CharField(
        max_length=512, blank=True, null=True,
        db_column='ten_chu_de',
        help_text="Tên Chủ đề - chỉ điền khi chapter_type=THEME (ví dụ: Vật lí nhiệt)"
    )
    # ──────────────────────────────────────────────────────────────────────────
    title = models.CharField(
        max_length=512,
        help_text="Tên hiển thị tổng hợp (= ten_chuong hoặc ten_chu_de, tùy chapter_type)"
    )
    chapter_number = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="Số thứ tự (ví dụ: '1', 'I', 'A')"
    )
    description = models.TextField(blank=True, null=True)
    order_num = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chapters'
        ordering = ['order_num']

    def __str__(self):
        type_label = "Chủ đề" if self.chapter_type == 'THEME' else "Chương"
        return f"[{self.subject.name}] {type_label}: {self.title}"


class Lesson(models.Model):
    """
    Bài học cụ thể thuộc một Chương/Chủ đề.
    Là đơn vị học tập chính của học sinh.
    """
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=512, help_text="Tên đầy đủ bài học")
    lesson_number = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="Số bài (ví dụ: '1', '2', '3') - lấy từ mục lục, không tách từ tên bài"
    )
    # Lưu vị trí trong PDF để phục vụ RAG
    page_start = models.IntegerField(
        null=True, blank=True,
        help_text="Trang bắt đầu (in trên sách)"
    )
    page_end = models.IntegerField(
        null=True, blank=True,
        help_text="Trang kết thúc (ước tính)"
    )
    # Trường content legacy (giữ lại để tương thích)
    content = models.TextField(
        blank=True, null=True,
        help_text="Tag [PAGE X-Y] hoặc nội dung tóm tắt"
    )
    order_num = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lessons'
        ordering = ['order_num']

    def __str__(self):
        return f"[{self.chapter.title}] Bài {self.lesson_number}: {self.title}"


class Topic(models.Model):
    """
    Mục nhỏ bên trong một Bài học.
    Là đơn vị gắn nhãn cho câu hỏi AI.
    """
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=512)
    content = models.TextField(blank=True, null=True, help_text="Nội dung lý thuyết tóm tắt")
    order_num = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'topics'
        ordering = ['order_num']

    def __str__(self):
        return f"{self.lesson.title} -> {self.title}"


class ContentChunk(models.Model):
    """
    Văn bản thô trích xuất từ PDF để phục vụ RAG.
    Gắn với Topic để phân loại kiến thức.
    """
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='chunks')
    raw_content = models.TextField()
    page_number = models.IntegerField(null=True, blank=True)
    chunk_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'content_chunks'
        ordering = ['chunk_index']

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.topic.title}"
