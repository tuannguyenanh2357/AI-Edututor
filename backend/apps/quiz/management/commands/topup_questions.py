"""
Management Command: topup_questions
Mục đích: Tự động phát hiện các CHƯƠNG có < min_questions câu và seed bổ sung
         cho đến khi đạt đủ ngưỡng tối thiểu (mặc định 20 câu/chương).
         
Chạy: python manage.py topup_questions
      python manage.py topup_questions --min_questions 25
      python manage.py topup_questions --subject_id 3
"""

import requests
import json
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.subjects.models import Subject
from apps.curriculum.models import Topic, Chapter
from apps.quiz.models import Quiz, Question, Answer
from django.conf import settings
import sys, io


class Command(BaseCommand):
    help = 'Top-up câu hỏi cho các chương đang thiếu, đảm bảo mỗi chương đủ số câu tối thiểu.'

    def add_arguments(self, parser):
        parser.add_argument('--min_questions', type=int, default=20,
                            help='Số câu hỏi tối thiểu cần có mỗi chương (mặc định: 20)')
        parser.add_argument('--subject_id', type=int, default=None,
                            help='Chỉ xử lý một môn học cụ thể (bỏ qua = tất cả môn)')
        parser.add_argument('--dry_run', action='store_true',
                            help='Chỉ hiển thị danh sách cần top-up, không gọi AI')

    def handle(self, *args, **options):
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        MIN_Q = options['min_questions']
        dry_run = options['dry_run']
        subject_id = options.get('subject_id')

        ai_base_url = getattr(settings, 'AI_SERVICE_BASE_URL', 'http://ai_service:8001').rstrip('/')
        ai_url = f"{ai_base_url}/api/v1/generate-quiz"
        headers = {"X-AI-Service-Key": settings.AI_SERVICE_KEY}

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  TOP-UP QUESTIONS — Mục tiêu: {MIN_Q} câu/chương")
        self.stdout.write(f"{'='*60}\n")

        # 1. Lấy danh sách môn cần xử lý
        if subject_id:
            subjects = Subject.objects.filter(id=subject_id)
        else:
            subjects = Subject.objects.all().order_by('grade_level', 'name')

        total_chapters_to_fix = 0
        total_added = 0

        for subject in subjects:
            self.stdout.write(f"\n📚 Môn: {subject.name} (Lớp {subject.grade_level})")

            # 2. Tìm tất cả chương của môn này
            chapters = Chapter.objects.filter(
                subject=subject
            ).prefetch_related('lessons__topics')

            for chapter in chapters:
                # Đếm số câu hỏi hiện tại của chương này (dùng chapter_title field)
                current_count = Question.objects.filter(
                    chapter_title=chapter.title
                ).count()

                if current_count >= MIN_Q:
                    continue  # Đã đủ → bỏ qua

                deficit = MIN_Q - current_count
                total_chapters_to_fix += 1

                self.stdout.write(
                    f"  ⚠️  Chương: {chapter.title[:55]} "
                    f"— hiện có {current_count} câu, cần thêm {deficit} câu"
                )

                if dry_run:
                    continue

                # 3. Lấy danh sách topics của chương, phân phối deficit đều
                all_topics = list(
                    Topic.objects.filter(lesson__chapter=chapter)
                    .annotate(q_count=Count('questions'))
                    .order_by('q_count')  # Ưu tiên topic ít câu nhất
                )

                if not all_topics:
                    self.stdout.write(f"       ❌ Không có topic nào, bỏ qua.")
                    continue

                # Phân phối: cho mỗi topic thêm (deficit / n_topics) câu, tối thiểu 1
                n = len(all_topics)
                per_topic_extra = max(1, (deficit + n - 1) // n)  # ceil division

                added_this_chapter = 0

                for topic in all_topics:
                    if added_this_chapter >= deficit:
                        break

                    # Số câu cần thêm cho topic này
                    to_add = min(per_topic_extra, deficit - added_this_chapter)
                    if to_add <= 0:
                        break

                    lesson = topic.lesson
                    chapter_obj = lesson.chapter
                    part = chapter_obj.part

                    breadcrumb = f"{subject.name}"
                    if part:
                        breadcrumb += f" > {part.title}"
                    type_label = "Chủ đề" if chapter_obj.chapter_type == 'THEME' else "Chương"
                    breadcrumb += f" > {type_label}: {chapter_obj.title}"
                    breadcrumb += f" > Bài {lesson.lesson_number}: {lesson.title}"
                    breadcrumb += f" > Mục: {topic.title}"

                    self.stdout.write(f"     🤖 Sinh {to_add} câu cho: {topic.title[:50]}...")

                    # Lấy context content
                    try:
                        from apps.curriculum.models import ContentChunk
                        chunks = ContentChunk.objects.filter(topic=topic).order_by('page_number', 'chunk_index')[:3]
                        context_text = "\n".join([c.raw_content for c in chunks]) if chunks.exists() else (topic.content or "")
                    except Exception:
                        context_text = topic.content or ""

                    payload = {
                        "subject_name": subject.name,
                        "grade_level": subject.grade_level,
                        "breadcrumb": breadcrumb,
                        "chapter_title": chapter_obj.title,
                        "num_questions": to_add,
                        "context": (
                            f"NGỮ CẢNH: {breadcrumb}\n"
                            f"NỘI DUNG SÁCH: {context_text[:3000]}\n\n"
                            f"YÊU CẦU: Sinh {to_add} câu hỏi trắc nghiệm Bloom 1-5. "
                            f"KHÔNG hỏi về hình ảnh. Bao phủ các mức độ nhận thức khác nhau."
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
                                    part_title=part.title if part else None,
                                    chapter_title=chapter_obj.title,
                                    chapter_type=chapter_obj.chapter_type,
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

                            added_this_chapter += len(questions_data)
                            total_added += len(questions_data)
                            self.stdout.write(self.style.SUCCESS(
                                f"       ✅ Thêm {len(questions_data)} câu. "
                                f"Chương now: {current_count + added_this_chapter} câu"
                            ))
                        else:
                            self.stdout.write(self.style.ERROR(f"       ❌ AI lỗi {resp.status_code}: {resp.text[:80]}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"       ❌ Kết nối lỗi: {str(e)}"))

        self.stdout.write(f"\n{'='*60}")
        if dry_run:
            self.stdout.write(f"  [DRY RUN] Số chương cần top-up: {total_chapters_to_fix}")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"  ✅ HOÀN THÀNH! Đã thêm {total_added} câu cho {total_chapters_to_fix} chương."
            ))
        self.stdout.write(f"{'='*60}\n")
