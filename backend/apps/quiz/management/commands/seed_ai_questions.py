import os
import requests
import json
from django.core.management.base import BaseCommand
from apps.subjects.models import Subject
from apps.curriculum.models import Topic, Chapter
from apps.quiz.models import Quiz, Question, Answer
from django.conf import settings

class Command(BaseCommand):
    help = 'Tự động sinh câu hỏi AI đảm bảo phủ kín 100% cấu trúc (Part > Chapter > Lesson > Topic)'

    def add_arguments(self, parser):
        parser.add_argument('--subject_id', type=int, help='ID môn học cụ thể')
        parser.add_argument('--limit', type=int, default=1000, help='Giới hạn số topic xử lý (mặc định 1000)')
        parser.add_argument('--clear', action='store_true', help='Xóa sạch câu hỏi cũ của môn học trước khi sinh mới')
        parser.add_argument('--questions_per_topic', type=int, default=5, help='Số câu hỏi cần có cho mỗi Topic')

    def handle(self, *args, **options):
        # Fix Unicode for Windows
        import sys, io
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        subject_id = options.get('subject_id')
        limit = options.get('limit')
        clear = options.get('clear')
        q_per_topic = options.get('questions_per_topic')

        if not subject_id and clear:
            self.stdout.write(self.style.ERROR("Dừng lại! Không thể dùng --clear cho TẤT CẢ các môn cùng lúc vì quá nguy hiểm. Vui lòng chỉ định --subject_id."))
            return

        # Xác định danh sách Subjects cần xử lý
        if subject_id:
            subjects = Subject.objects.filter(id=subject_id)
        else:
            self.stdout.write(self.style.WARNING("Chế độ: Chạy cho TẤT CẢ các môn học..."))
            subjects = Subject.objects.all()

        for subject in subjects:
            self.stdout.write(f"\n{'*'*40}\n📦 Xử lý môn: {subject.name} (ID: {subject.id})\n{'*'*40}")
            
            # 1. Dọn dẹp nếu yêu cầu (Chỉ chạy khi có subject_id cụ thể)
            if clear:
                self.stdout.write(self.style.WARNING(f"   🧹 Đang xóa sạch câu hỏi cũ của môn: {subject.name}..."))
                Question.objects.filter(topic__lesson__chapter__subject=subject).delete()
                self.stdout.write(self.style.SUCCESS("   Đã dọn dẹp xong."))

            # 2. Tìm các Topic chưa đủ chỉ tiêu trong môn này
            from django.db.models import Count
            all_topics = Topic.objects.filter(lesson__chapter__subject=subject)
            total_topics_count = all_topics.count()
            
            if total_topics_count == 0:
                self.stdout.write(self.style.WARNING(f"   ⚠️ Bỏ qua: Môn này chưa có cấu trúc mục lục (TOC). Hãy chạy sync_textbooks trước."))
                continue

            query = all_topics.annotate(q_count=Count('questions')).filter(q_count__lt=q_per_topic)
            topics_to_seed = query.order_by(
                'lesson__chapter__order_num', 
                'lesson__order_num', 
                'order_num'
            )[:limit]

            needed_count = topics_to_seed.count()
            if needed_count == 0:
                self.stdout.write(self.style.SUCCESS(f"   🎉 Đã phủ kín 100% ({total_topics_count}/{total_topics_count} topics)."))
                continue

            self.stdout.write(f"   🚀 Cần nạp thêm cho {needed_count}/{total_topics_count} topics.")
            
            ai_base_url = getattr(settings, 'AI_SERVICE_BASE_URL', 'http://ai_service:8001').rstrip('/')
            ai_url = f"{ai_base_url}/api/v1/generate-quiz"
            headers = {"X-AI-Service-Key": settings.AI_SERVICE_KEY}

            for i, topic in enumerate(topics_to_seed):
                lesson = topic.lesson
                chapter = lesson.chapter
                part = chapter.part
                
                breadcrumb = f"{subject.name}"
                if part: breadcrumb += f" > {part.title}"
                type_label = "Chủ đề" if chapter.chapter_type == 'THEME' else "Chương"
                breadcrumb += f" > {type_label}: {chapter.title}"
                breadcrumb += f" > Bài {lesson.lesson_number}: {lesson.title}"
                breadcrumb += f" > Mục: {topic.title}"

                self.stdout.write(f"\n   [{i+1}/{needed_count}] 🧠 Đang sinh cho: {breadcrumb}")

                from apps.curriculum.models import ContentChunk
                chunks = ContentChunk.objects.filter(topic=topic).order_by('page_number', 'chunk_index')[:3]
                context_text = "\n".join([c.raw_content for c in chunks]) if chunks.exists() else (topic.content or "")

                payload = {
                    "subject_name": subject.name,
                    "grade_level": subject.grade_level,
                    "breadcrumb": breadcrumb,
                    "chapter_title": chapter.title,
                    "num_questions": q_per_topic,
                    "context": (
                        f"NGỮ CẢNH: {breadcrumb}\n"
                        f"NỘI DUNG SÁCH: {context_text[:4000]}\n\n"
                        f"YÊU CẦU: Sinh {q_per_topic} câu hỏi trắc nghiệm Bloom 1-5. KHÔNG hỏi về hình ảnh."
                    )
                }

                try:
                    resp = requests.post(ai_url, json=payload, headers=headers, timeout=300)
                    if resp.status_code == 200:
                        data = resp.json()
                        questions_data = data.get('questions', [])
                        
                        quiz, _ = Quiz.objects.get_or_create(
                            subject=subject,
                            quiz_type='PRACTICE',
                            defaults={'title': f'Luyện tập: {subject.name}'}
                        )

                        for q_data in questions_data:
                            q = Question.objects.create(
                                quiz=quiz,
                                topic=topic,
                                question_text=q_data['question'],
                                question_type='MCQ',
                                part_title=chapter.part.title if chapter.part else None,
                                chapter_title=chapter.title,
                                chapter_type=chapter.chapter_type,
                                lesson_title=lesson.title,
                                lesson_number=lesson.lesson_number,
                                subject_name=subject.name,
                                grade_level=subject.grade_level,
                                explanation=q_data.get('explanation', ''),
                                bloom_level=int(q_data.get('bloom_level', 1)),
                                difficulty_level=int(q_data.get('bloom_level', 1)),
                                difficulty_score=float(q_data.get('difficulty_score', 1.0))
                            )
                            for idx, opt in enumerate(q_data['options']):
                                Answer.objects.create(
                                    question=q,
                                    answer_text=opt,
                                    is_correct=(idx == q_data['correct_index']),
                                    order_num=idx
                                )
                        self.stdout.write(self.style.SUCCESS(f"      ✅ OK: {len(questions_data)} câu."))
                    else:
                        self.stdout.write(self.style.ERROR(f"      ❌ Lỗi AI: {resp.text[:100]}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"      ❌ Lỗi kết nối: {str(e)}"))

        self.stdout.write(f"\n✅ TẤT CẢ CÁC MÔN ĐÃ ĐƯỢC XỬ LÝ XONG!")
