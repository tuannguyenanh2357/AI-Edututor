import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.curriculum.models import Chapter, Lesson

chapters = Chapter.objects.filter(title__icontains='MỆNH ĐỀ VÀ TẬP HỢP')
for ch in chapters:
    print(f"Chapter ID: {ch.id} | Title: {ch.title} | Subject: {ch.subject.name} (Lớp {ch.subject.grade_level})")
    lessons = Lesson.objects.filter(chapter=ch).order_by('order_num')
    for l in lessons:
        print(f"  - Lesson ID: {l.id} | No: {l.lesson_number} | Title: {l.title}")
