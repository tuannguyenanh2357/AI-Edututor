from django.db import models

class Subject(models.Model):
    GRADE_CHOICES = [
        (10, 'Lớp 10'),
        (11, 'Lớp 11'),
        (12, 'Lớp 12'),
    ]
    name = models.CharField(max_length=50) # Remove unique here
    grade_level = models.IntegerField(choices=GRADE_CHOICES, default=12)
    description = models.TextField(blank=True, null=True)
    icon_url = models.TextField(blank=True, null=True)
    page_offset = models.IntegerField(default=0, help_text="Số trang cần bù để khớp trang in và trang PDF")

    class Meta:
        db_table = 'subjects'
        unique_together = ('name', 'grade_level')

    def __str__(self):
        return self.name

class SubjectStat(models.Model):
    subject = models.OneToOneField(Subject, on_delete=models.CASCADE, related_name='stats')
    total_students = models.IntegerField(default=0)
    active_students = models.IntegerField(default=0)
    chat_sessions = models.IntegerField(default=0)
    learning_paths_created = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=0)
    trend_last_7days = models.CharField(max_length=30, blank=True, null=True)
    last_calculated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'subject_stats'

class SubjectDocument(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Extracted text content from the textbook", blank=True, null=True)
    pdf_file = models.FileField(upload_to='books/pdfs/', help_text="Upload original PDF textbook", max_length=100, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subject_documents'

    def __str__(self):
        return f"{self.subject.name} - {self.title}"
