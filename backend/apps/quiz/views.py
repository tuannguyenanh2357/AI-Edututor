import os
import httpx
from django.conf import settings
from django.utils import timezone
from django.db import models
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Quiz, Question, Answer, QuizSubmission
from .serializers import (
    QuizSerializer, QuizSubmissionSerializer,
    PreTestSubmitSerializer, QuestionWithAnswerSerializer,
    QuestionSerializer
)
from .services import AIEvaluatorService
from apps.users.models import LearningPath

AI_SERVICE_URL = settings.AI_SERVICE_URL
AI_SERVICE_KEY = settings.AI_SERVICE_KEY
AI_HEADERS = {"X-AI-Service-Key": AI_SERVICE_KEY}


# ─── Practice Quiz APIs (đã có) ───────────────────────────────────────────────

class QuizDetailView(generics.RetrieveAPIView):
    queryset = Quiz.objects.prefetch_related('questions__answers').all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuizListView(generics.ListAPIView):
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        subject_id = self.request.query_params.get('subject_id')
        quiz_type = self.request.query_params.get('quiz_type', 'PRACTICE')
        qs = Quiz.objects.all()
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        if quiz_type:
            qs = qs.filter(quiz_type=quiz_type)
        return qs


class QuizSubmissionView(generics.CreateAPIView):
    serializer_class = QuizSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ─── Pre-Test APIs (mới) ──────────────────────────────────────────────────────

class PreTestView(APIView):
    """
    GET /api/quiz/pre-test/?subject_id=<id>
    Lấy bộ câu hỏi pre-test. Nếu chưa có trong DB → AI sinh tự động.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subject_id = request.query_params.get('subject_id')
        if not subject_id:
            return Response({"error": "subject_id là bắt buộc."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.subjects.models import Subject
            from apps.curriculum.models import Chapter
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({"error": "Môn học không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Tìm pre-test đã tồn tại cho môn này
        quiz = Quiz.objects.filter(subject=subject, quiz_type='PRE_TEST').first()

        if not quiz:
            # 2. Kiểm tra xem có đủ câu hỏi trong DB để tự tạo Pre-test không
            # Lấy tất cả câu hỏi thuộc Môn học này thông qua Topic -> Lesson -> Chapter
            db_questions = Question.objects.filter(topic__lesson__chapter__subject=subject)
            
            if db_questions.count() >= 10:
                # Tự xây dựng bộ đề từ kho câu hỏi sẵn có
                quiz = self._build_quiz_from_db(subject, db_questions)
            else:
                # Nếu kho câu hỏi quá ít (< 10 câu), gọi AI Service sinh mới (luồng cũ)
                try:
                    response = httpx.post(
                        f"{AI_SERVICE_URL}/api/v1/generate-pretest",
                        json={
                            "subject_name": subject.name,
                            "grade_level": subject.grade_level,
                            "num_questions": 10,
                            "context": (
                                "YÊU CẦU PHÂN TẦNG BLOOM (1-6):\n"
                                "- 4 câu Mức 1-2 (Nhận biết/Thông hiểu)\n"
                                "- 4 câu Mức 3-4 (Vận dụng/Phân tích)\n"
                                "- 2 câu Mức 5-6 (Đánh giá/Sáng tạo)\n"
                                "Đảm bảo mỗi câu có bloom_level và difficulty_score chính xác."
                            )
                        },
                        headers=AI_HEADERS,
                        timeout=60.0
                    )
                    response.raise_for_status()
                    ai_data = response.json()
                    quiz = self._save_ai_quiz(ai_data, subject)
                except Exception as e:
                    return Response({"error": f"Lỗi tạo pre-test: {str(e)}"}, status=500)

        return Response(QuizSerializer(quiz).data)

    def _build_quiz_from_db(self, subject, all_questions):
        """Xây dựng bài thi đầu vào từ kho câu hỏi sẵn có trong DB."""
        import random
        quiz = Quiz.objects.create(
            subject=subject,
            quiz_type='PRE_TEST',
            title=f"Đánh giá năng lực: {subject.name} Lớp {subject.grade_level}",
            description="Bài kiểm tra dựa trên kho câu hỏi chuẩn để xây dựng lộ trình học tập.",
            difficulty='MIXED',
            passing_score=50
        )
        
        # Chọn ngẫu nhiên 10 câu hỏi để tạo đề
        selected_questions = random.sample(list(all_questions), min(10, all_questions.count()))
        
        # Sao chép/Liên kết câu hỏi vào Quiz mới (tùy thuộc vào việc bạn muốn dùng chung Question hay copy)
        # Ở đây tôi sẽ liên kết trực tiếp bằng cách gán quiz_id (vì Question FK quiz)
        # Lưu ý: Trong thực tế nên tạo bảng trung gian nếu 1 Question thuộc nhiều Quiz
        for i, q in enumerate(selected_questions, start=1):
            q.quiz = quiz
            q.order_num = i
            q.save()
            
        return quiz

    def _save_ai_quiz(self, ai_data, subject):
        """Lưu câu hỏi AI sinh vào database."""
        quiz = Quiz.objects.create(
            subject=subject,
            quiz_type='PRE_TEST',
            title=f"Pre-Test: {subject.name} Lớp {subject.grade_level}",
            description="Bài kiểm tra đầu vào để AI xây dựng lộ trình học tập phù hợp.",
            difficulty='MIXED',
            passing_score=50,
            chapter_coverage=[q.get('chapter_title', '') for q in ai_data.get('questions', [])]
        )

        for i, q_data in enumerate(ai_data.get('questions', []), start=1):
            question = Question.objects.create(
                quiz=quiz,
                question_text=q_data['question'],
                question_type='MCQ',
                chapter_title=q_data.get('chapter_title', ''),
                explanation=q_data.get('explanation', ''),
                bloom_level=int(q_data.get('bloom_level', 1)),
                difficulty_level=int(q_data.get('difficulty_score', 1)),
                order_num=i
            )
            for j, option_text in enumerate(q_data.get('options', [])):
                Answer.objects.create(
                    question=question,
                    answer_text=option_text,
                    is_correct=(j == q_data.get('correct_index', 0)),
                    order_num=j
                )

        return Quiz.objects.prefetch_related('questions__answers').get(id=quiz.id)


class PreTestSubmitView(APIView):
    """
    POST /api/quiz/pre-test/submit/
    Nộp bài pre-test. Tính điểm → lưu submission → kích hoạt AI Evaluator.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PreTestSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        quiz_id = serializer.validated_data['quiz_id']
        user_answers = serializer.validated_data['answers']

        try:
            quiz = Quiz.objects.prefetch_related('questions__answers').get(
                id=quiz_id, quiz_type='PRE_TEST'
            )
        except Quiz.DoesNotExist:
            return Response({"error": "Pre-test không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        # ── Per-chapter & Per-Bloom scoring ─────────────────────────────────
        questions = list(quiz.questions.prefetch_related('answers').all())
        total = len(questions)
        correct_count = 0
        wrong_chapters = []
        answers_data = {}
        chapter_stats: dict = {}
        bloom_stats: dict = {i: {"correct": 0, "total": 0} for i in range(1, 7)}

        for question in questions:
            chosen_answer_id = user_answers.get(str(question.id))
            answers_data[str(question.id)] = chosen_answer_id

            # Chapter Stats
            ch = question.chapter_title or "Kiến thức chung"
            if ch not in chapter_stats:
                chapter_stats[ch] = {"correct": 0, "total": 0}
            chapter_stats[ch]["total"] += 1

            # Bloom Stats
            bl = question.difficulty_level or 1
            bloom_stats[bl]["total"] += 1

            correct_answer = question.answers.filter(is_correct=True).first()
            if correct_answer and chosen_answer_id == correct_answer.id:
                correct_count += 1
                chapter_stats[ch]["correct"] += 1
                bloom_stats[bl]["correct"] += 1
            else:
                if ch not in wrong_chapters:
                    wrong_chapters.append(ch)

        # Convert to analysis data
        chapter_scores = {
            ch: round((stats["correct"] / stats["total"]) * 100, 1)
            for ch, stats in chapter_stats.items()
        }
        bloom_analysis = {
            f"bloom_{bl}": round((stats["correct"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 100
            for bl, stats in bloom_stats.items()
        }

        score = round((correct_count / total) * 100, 2) if total > 0 else 0
        passed = score >= 80

        # ── Lưu submission ────────────────────────────────────────────────────
        submission = QuizSubmission.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            answers_data=answers_data,
            wrong_chapters=wrong_chapters,
            bloom_analysis=bloom_analysis,
            passed=passed
        )

        # ── Kích hoạt AI Evaluator (via Service) ──────────────────────────────
        AIEvaluatorService.trigger_pretest_evaluation(
            user_id=request.user.id,
            subject_id=quiz.subject_id,
            subject_name=quiz.subject.name,
            grade_level=request.user.grade_level,
            score=score,
            wrong_chapters=wrong_chapters,
            chapter_scores=chapter_scores
        )

        return Response({
            "submission_id": submission.id,
            "score": score,
            "correct_count": correct_count,
            "total_questions": total,
            "passed": passed,
            "wrong_chapters": wrong_chapters,
            "message": "AI đang phân tích và tạo lộ trình học tập cho bạn..."
        }, status=status.HTTP_201_CREATED)


class PreTestResultView(APIView):
    """
    GET /api/quiz/pre-test/result/<submission_id>/
    Polling endpoint: Kiểm tra LearningPath đã được tạo chưa dựa trên submission.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, submission_id):
        from django.shortcuts import get_object_or_404
        from .models import QuizSubmission
        from apps.users.models import LearningPath

        submission = get_object_or_404(QuizSubmission, id=submission_id, user=request.user)
        subject_id = submission.quiz.subject_id

        path = LearningPath.objects.filter(
            user=request.user,
            subject_id=subject_id
        ).first()

        if not path or path.status == 'PENDING':
            return Response({
                "score": submission.score,
                "evaluator_status": "evaluating",
                "learning_path_id": None
            })

        # Khi đã hoàn thành -> trả về kết quả chi tiết
        questions = submission.quiz.questions.prefetch_related('answers').all()
        q_serializer = QuestionWithAnswerSerializer(questions, many=True)

        return Response({
            "score": submission.score,
            "evaluator_status": "completed",
            "learning_path_id": path.id,
            "subject_id": path.subject_id,
            "subject_name": path.subject.name,
            "ai_feedback": path.ai_feedback,
            "bloom_analysis": submission.bloom_analysis,
            "questions": q_serializer.data,
            "user_answers": submission.answers_data,   # {str(question_id): answer_id}
            "wrong_chapters": submission.wrong_chapters,
            "correct_count": submission.quiz.questions.count() - len(submission.wrong_chapters)
        })


class ChapterTestView(APIView):
    """
    GET /api/quiz/chapter-test/?chapter_id=<id>[&mode=post_test]
    Lay danh sach cau hoi cho mot chuong cu the.

    mode=chapter_test (default): Đánh giá đầu vào — random stratified, ưu tiên câu chưa làm.
    mode=post_test: Vượt ải Mastery — 70% câu từ topic RED/YELLOW của LearningPath.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        chapter_id = request.query_params.get('chapter_id')
        mode = request.query_params.get('mode', 'chapter_test')  # 'chapter_test' | 'post_test'
        print(f"DEBUG: ChapterTestView called with chapter_id={chapter_id}, mode={mode}")
        if not chapter_id:
            return Response({"error": "chapter_id la bat buoc."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.curriculum.models import Chapter
            chapter = Chapter.objects.select_related('subject').get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"error": "Chuong khong ton tai."}, status=status.HTTP_404_NOT_FOUND)

        # Lay tat ca cau hoi thuoc chuong nay (qua topic -> lesson -> chapter)
        all_q = Question.objects.filter(
            topic__lesson__chapter=chapter
        ).prefetch_related('answers').select_related('topic')

        if all_q.count() < 5:
            print(f"DEBUG: Not enough questions for chapter {chapter_id} (found {all_q.count()}). Fallback...")
            all_q = Question.objects.filter(
                models.Q(topic__lesson__chapter__subject=chapter.subject) |
                models.Q(quiz__subject=chapter.subject)
            ).distinct().prefetch_related('answers')

            if all_q.count() < 5:
                return Response(
                    {"error": f"Môn học {chapter.subject.name} hiện chưa có đủ câu hỏi (mới có {all_q.count()} câu). Đang trong quá trình nạp dữ liệu AI..."},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Lấy lịch sử câu hỏi đã làm của user cho chương này (anti-repeat)
        from apps.users.models import LearningPath
        seen_question_ids = self._get_seen_question_ids(request.user, chapter)

        # Lấy mastery_map nếu là post_test
        weak_topic_names = []
        if mode == 'post_test':
            weak_topic_names = self._get_weak_topics(request.user, chapter)
            print(f"DEBUG: Post-test weak topics: {weak_topic_names}")

        selected_questions = self._select_balanced_questions(
            all_q, chapter,
            seen_ids=seen_question_ids,
            weak_topics=weak_topic_names,
            is_post_test=(mode == 'post_test')
        )

        serializer = QuestionSerializer(selected_questions, many=True)
        print(f"DEBUG: Selected {len(selected_questions)} questions | mode={mode}")
        return Response({
            "chapter_id": chapter.id,
            "chapter_title": chapter.title,
            "subject_id": chapter.subject.id,
            "subject_name": chapter.subject.name,
            "mode": mode,
            "total_questions": len(selected_questions),
            "questions": serializer.data
        })

    def _get_seen_question_ids(self, user, chapter) -> set:
        """Trả về set các question_id mà user đã từng làm ở chương này."""
        from .models import QuizSubmission
        seen_ids = set()
        # Tìm tất cả submission của user liên quan đến chương này
        submissions = QuizSubmission.objects.filter(
            user=user,
            quiz__chapter_coverage__contains=chapter.title
        ).values_list('answers_data', flat=True)
        for answers_data in submissions:
            if isinstance(answers_data, dict):
                seen_ids.update(int(k) for k in answers_data.keys() if k.isdigit())
        return seen_ids

    def _get_weak_topics(self, user, chapter) -> list:
        """Trả về danh sách tên topic mà user đang yếu (RED/YELLOW) cho chương này."""
        from apps.users.models import LearningPath
        weak_topics = []
        try:
            path = LearningPath.objects.filter(user=user, chapter=chapter).first()
            if path and path.ai_feedback:
                # Trích xuất mastery_map từ ai_feedback nếu được lưu ở đó
                # Hoặc truy vấn LearningPathItem với mastery_level=RED/YELLOW
                from apps.users.models import LearningPathItem, LearningProgress
                weak_items = LearningProgress.objects.filter(
                    user=user,
                    learning_path_item__learning_path=path,
                    mastery_level__in=['RED', 'YELLOW']
                ).select_related('learning_path_item__topic', 'learning_path_item__lesson')

                for item in weak_items:
                    lpi = item.learning_path_item
                    if lpi.topic:
                        weak_topics.append(lpi.topic.title)
                    elif lpi.lesson:
                        weak_topics.append(lpi.lesson.title)
        except Exception as e:
            print(f"⚠️ _get_weak_topics error: {e}")
        return weak_topics

    def _select_balanced_questions(self, all_q, chapter, seen_ids: set = None, weak_topics: list = None, is_post_test: bool = False):
        """
        Chọn chính xác 20 câu hỏi với 2 chế độ:
        - chapter_test (default): Stratified Sampling, ưu tiên câu chưa từng làm (anti-repeat).
        - post_test: 70% câu từ topic RED/YELLOW, 30% câu ôn tổng hợp.
        """
        import random
        from apps.curriculum.models import Lesson

        TARGET_COUNT = 20
        seen_ids = seen_ids or set()
        weak_topics = weak_topics or []
        all_q_list = list(all_q)

        if not all_q_list:
            return []

        # ── POST-TEST MODE: ưu tiên topic yếu ──────────────────────────────────
        if is_post_test and weak_topics:
            # Tách câu thuộc topic yếu vs câu tổng hợp
            weak_pool = [q for q in all_q_list if getattr(q.topic, 'title', '') in weak_topics]
            other_pool = [q for q in all_q_list if q not in weak_pool]

            # Ưu tiên câu chưa làm trong từng pool
            unseen_weak = [q for q in weak_pool if q.id not in seen_ids]
            unseen_other = [q for q in other_pool if q.id not in seen_ids]
            seen_weak = [q for q in weak_pool if q.id in seen_ids]
            seen_other = [q for q in other_pool if q.id in seen_ids]

            # 70% slot cho topic yếu, 30% slot cho tổng hợp
            weak_slots = min(round(TARGET_COUNT * 0.70), len(weak_pool))
            other_slots = TARGET_COUNT - weak_slots

            selected = []
            # Điền slot topic yếu: ưu tiên câu chưa làm
            for pool in [unseen_weak, seen_weak]:
                need = weak_slots - len(selected)
                if need <= 0:
                    break
                selected += random.sample(pool, min(need, len(pool)))
            # Điền slot tổng hợp
            other_selected = []
            for pool in [unseen_other, seen_other]:
                need = other_slots - len(other_selected)
                if need <= 0:
                    break
                other_selected += random.sample(pool, min(need, len(pool)))
            selected += other_selected

            # Nếu vẫn thiếu, lấy bù từ pool còn lại
            if len(selected) < TARGET_COUNT:
                used_ids = {q.id for q in selected}
                remaining = [q for q in all_q_list if q.id not in used_ids]
                need = TARGET_COUNT - len(selected)
                selected += random.sample(remaining, min(need, len(remaining)))

            random.shuffle(selected)
            return selected[:TARGET_COUNT]

        # ── CHAPTER TEST MODE: Stratified Sampling + Anti-Repeat ───────────────
        lessons = list(Lesson.objects.filter(chapter=chapter).order_by('order_num'))
        num_lessons = len(lessons)

        if not lessons or len(all_q_list) <= TARGET_COUNT:
            # Ít câu: ưu tiên câu chưa làm, rồi mới lấy câu đã làm
            unseen = [q for q in all_q_list if q.id not in seen_ids]
            seen_q = [q for q in all_q_list if q.id in seen_ids]
            pool = unseen + seen_q
            return random.sample(pool, min(TARGET_COUNT, len(pool)))

        quota_per_lesson = TARGET_COUNT // num_lessons
        extra_slots = TARGET_COUNT % num_lessons
        selected_ids = set()
        selected_objs = []

        for i, lesson in enumerate(lessons):
            lesson_qs = list(all_q.filter(topic__lesson=lesson))
            current_quota = quota_per_lesson + (1 if i < extra_slots else 0)

            # Tách câu chưa làm vs đã làm trong bài này
            unseen = [q for q in lesson_qs if q.id not in seen_ids]
            seen_q = [q for q in lesson_qs if q.id in seen_ids]
            # Ưu tiên câu chưa làm
            available = unseen + seen_q

            if len(available) <= current_quota:
                for q in available:
                    if q.id not in selected_ids:
                        selected_objs.append(q)
                        selected_ids.add(q.id)
            else:
                # Đa dạng Bloom: chia dễ (1-3) và khó (4-6), nhưng ưu tiên unseen trước
                unseen_easy = [q for q in unseen if (q.difficulty_level or 1) <= 3]
                unseen_hard = [q for q in unseen if (q.difficulty_level or 1) >= 4]
                seen_easy = [q for q in seen_q if (q.difficulty_level or 1) <= 3]
                seen_hard = [q for q in seen_q if (q.difficulty_level or 1) >= 4]

                half = current_quota // 2
                picks = []
                # Ưu tiên unseen theo Bloom
                for easy_pool, hard_pool in [(unseen_easy, unseen_hard), (seen_easy, seen_hard)]:
                    if len(picks) >= current_quota:
                        break
                    need_easy = min(half, len(easy_pool), current_quota - len(picks))
                    need_hard = min(current_quota - len(picks) - need_easy, len(hard_pool))
                    if easy_pool and hard_pool:
                        picks += random.sample(easy_pool, need_easy)
                        picks += random.sample(hard_pool, need_hard)
                    elif easy_pool:
                        picks += random.sample(easy_pool, min(current_quota - len(picks), len(easy_pool)))
                    elif hard_pool:
                        picks += random.sample(hard_pool, min(current_quota - len(picks), len(hard_pool)))

                if len(picks) < current_quota:
                    remaining = [q for q in available if q not in picks]
                    picks += random.sample(remaining, min(current_quota - len(picks), len(remaining)))

                for q in picks[:current_quota]:
                    if q.id not in selected_ids:
                        selected_objs.append(q)
                        selected_ids.add(q.id)

        # Vòng 2: bù thiếu
        deficit = TARGET_COUNT - len(selected_objs)
        if deficit > 0:
            remaining_pool = [q for q in all_q_list if q.id not in selected_ids]
            # Ưu tiên câu chưa làm khi bù
            unseen_rem = [q for q in remaining_pool if q.id not in seen_ids]
            seen_rem = [q for q in remaining_pool if q.id in seen_ids]
            fill = unseen_rem + seen_rem
            selected_objs += random.sample(fill, min(deficit, len(fill)))

        random.shuffle(selected_objs)
        return selected_objs[:TARGET_COUNT]

class ChapterTestSubmitView(APIView):
    """
    POST /api/quiz/chapter-test/submit/
    Nộp bài Chapter Test (= Đánh giá đầu vào theo chương).
    Tính điểm → lưu QuizSubmission → kích hoạt AI → trả submission_id để Frontend polling.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.curriculum.models import Chapter

        chapter_id = request.data.get('chapter_id')
        user_answers = request.data.get('answers')  # {str(question_id): answer_id}

        if not chapter_id or not user_answers:
            return Response({"error": "Thiếu thông tin nộp bài."}, status=400)

        try:
            chapter = Chapter.objects.select_related('subject').get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"error": "Chương không tồn tại."}, status=404)

        # ── Lấy lại danh sách câu hỏi để tính điểm và luưu submission ────────────
        question_ids = [int(qid) for qid in user_answers.keys()]
        questions = Question.objects.filter(id__in=question_ids).prefetch_related('answers')

        correct_count = 0
        total = questions.count()
        wrong_details = []
        answers_data = {}
        bloom_stats: dict = {i: {"correct": 0, "total": 0} for i in range(1, 7)}

        for q in questions:
            chosen_id = user_answers.get(str(q.id))
            answers_data[str(q.id)] = chosen_id
            
            bl = q.difficulty_level or 1
            bloom_stats[bl]["total"] += 1

            correct_ans = q.answers.filter(is_correct=True).first()
            if correct_ans and chosen_id == correct_ans.id:
                correct_count += 1
                bloom_stats[bl]["correct"] += 1
            else:
                user_ans_obj = q.answers.filter(id=chosen_id).first()
                wrong_details.append({
                    "question": q.question_text,
                    "student_chose": user_ans_obj.answer_text if user_ans_obj else "Không chọn",
                    "correct_answer": correct_ans.answer_text if correct_ans else "N/A",
                    "topic": getattr(q.topic, 'title', getattr(q, 'chapter_title', chapter.title)),
                    "bloom_level": bl
                })

        score = round((correct_count / total) * 100, 2) if total > 0 else 0
        bloom_analysis = {
            f"bloom_{bl}": round((stats["correct"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 100
            for bl, stats in bloom_stats.items()
        }

        # ── Tìm hoặc tạo Quiz đại diện (chapter-test quiz) để gắn vào Submission ────────
        # Dùng quiz_type='CHAPTER_TEST', mỗi chương 1 quiz virtual
        quiz = Quiz.objects.filter(
            subject=chapter.subject,
            quiz_type='CHAPTER_TEST',
            chapter_coverage__contains=chapter.title
        ).first()

        if not quiz:
            # Tạo Quiz virtual nếu chưa có
            quiz = Quiz.objects.create(
                subject=chapter.subject,
                quiz_type='CHAPTER_TEST',
                title=f"Kiểm tra chương: {chapter.title}",
                passing_score=80,
                chapter_coverage=[chapter.title]
            )

        # ── Lưu QuizSubmission ──────────────────────────────────────────────────────
        submission = QuizSubmission.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            answers_data=answers_data,
            wrong_chapters=[d["topic"] for d in wrong_details], # backward compat
            bloom_analysis=bloom_analysis,
            passed=(score >= 80) # 80% Mastery Threshold
        )

        # ── [MỚI] Đảm bảo LearningPath ở trạng thái PENDING để AI Evaluator nhận diện đúng là Pre-test ──
        path, _ = LearningPath.objects.get_or_create(
            user=request.user,
            chapter=chapter,
            defaults={
                "subject": chapter.subject,
                "status": "PENDING",
                "pre_test_score": score
            }
        )
        # Nếu đã tồn tại (ví dụ trạng thái LOCKED từ chương trước), phải chuyển sang PENDING
        if path.status != 'PENDING':
            path.status = 'PENDING'
            path.pre_test_score = score
            path.save()

        # ── Kích hoạt AI Evaluator (chapter-based) ───────────────────────────────
        AIEvaluatorService.trigger_chapter_evaluation(
            user_id=request.user.id,
            subject_id=chapter.subject.id,
            chapter_id=chapter.id,
            chapter_title=chapter.title,
            subject_name=chapter.subject.name,
            grade_level=request.user.grade_level,
            score=score,
            wrong_details=wrong_details
        )

        return Response({
            "submission_id": submission.id,
            "score": score,
            "correct_count": correct_count,
            "total_questions": total,
            "passed": score >= 80,
            "message": "AI đang phân tích và tạo lộ trình học tập cho bạn..."
        }, status=status.HTTP_201_CREATED)


class ChapterTestResultView(APIView):
    """
    GET /api/quiz/chapter-test/result/<submission_id>/
    Polling endpoint: Kiểm tra LearningPath (chapter-based) đã được tạo chưa.
    Dùng chung component pre-test-result ở Frontend.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, submission_id):
        from django.shortcuts import get_object_or_404
        from apps.users.models import LearningPath
        from apps.curriculum.models import Chapter

        submission = get_object_or_404(QuizSubmission, id=submission_id, user=request.user)

        # Lấy chapter từ chapter_coverage của quiz
        chapter_coverage = submission.quiz.chapter_coverage or []
        chapter_title = chapter_coverage[0] if chapter_coverage else None
        chapter = None
        if chapter_title:
            chapter = Chapter.objects.filter(
                subject=submission.quiz.subject,
                title=chapter_title
            ).first()

        # Tìm LearningPath theo chapter (bao gồm cả PENDING)
        path = None
        if chapter:
            path = LearningPath.objects.filter(
                user=request.user,
                chapter=chapter
            ).first()

        if not path:
            return Response({
                "score": float(submission.score),
                "evaluator_status": "evaluating",
                "learning_path_id": None
            })

        if path.status == 'PENDING':
            # Kiểm tra xem có bị treo không (ví dụ quá 2 phút chưa xong)
            import datetime
            now = timezone.now()
            if (now - path.updated_at).total_seconds() > 120:
                 return Response({
                    "score": float(submission.score),
                    "evaluator_status": "failed",
                    "error_message": "AI analysis timed out. Please try again or contact support.",
                    "learning_path_id": None
                })
            
            return Response({
                "score": float(submission.score),
                "evaluator_status": "evaluating",
                "learning_path_id": None
            })

        # Đã có LearningPath → trả kết quả đầy đủ
        questions = Question.objects.filter(
            id__in=submission.answers_data.keys()
        ).prefetch_related('answers')
        q_serializer = QuestionWithAnswerSerializer(questions, many=True)

        # Tìm chương kế tiếp
        next_chapter = None
        if chapter:
            if chapter.order_num is not None:
                next_chapter = Chapter.objects.filter(
                    subject=submission.quiz.subject,
                    order_num__gt=chapter.order_num
                ).order_by('order_num').first()
            
            # Fallback nếu không có order_num hoặc không tìm thấy theo order_num
            if not next_chapter:
                next_chapter = Chapter.objects.filter(
                    subject=submission.quiz.subject,
                    id__gt=chapter.id
                ).order_by('id').first()

        return Response({
            "score": float(submission.score),
            "evaluator_status": "completed",
            "learning_path_id": path.id,
            "subject_id": submission.quiz.subject_id,
            "subject_name": submission.quiz.subject.name,
            "chapter_id": chapter.id if chapter else None,
            "chapter_title": chapter.title if chapter else None,
            "next_chapter_id": next_chapter.id if next_chapter else None,
            "ai_feedback": path.ai_feedback,
            "bloom_analysis": submission.bloom_analysis,
            "questions": q_serializer.data,
            "user_answers": submission.answers_data,
            "wrong_chapters": submission.wrong_chapters,
            "correct_count": int(submission.score * questions.count() / 100)
        })


class PostTestSubmitView(APIView):
    """
    POST /api/quiz/post-test/submit/
    Nộp bài kiểm tra cuối chương (Post-test).
    - Lấy câu hỏi theo chapter, tính điểm
    - Kích hoạt AI để so sánh Pre-test vs Post-test và đưa ra nhận xét
    - Trả về submission_id để Frontend polling
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.curriculum.models import Chapter

        chapter_id = request.data.get('chapter_id')
        user_answers = request.data.get('answers')  # {str(question_id): answer_id}

        if not chapter_id or not user_answers:
            return Response({"error": "Thiếu thông tin nộp bài."}, status=400)

        try:
            chapter = Chapter.objects.select_related('subject').get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"error": "Chương không tồn tại."}, status=404)

        # ── Tính điểm ─────────────────────────────────────────────────────────
        question_ids = [int(qid) for qid in user_answers.keys()]
        questions = Question.objects.filter(id__in=question_ids).prefetch_related('answers')

        correct_count = 0
        total = questions.count()
        wrong_details = []
        answers_data = {}

        for q in questions:
            chosen_id = user_answers.get(str(q.id))
            answers_data[str(q.id)] = chosen_id

            correct_ans = q.answers.filter(is_correct=True).first()
            if correct_ans and chosen_id == correct_ans.id:
                correct_count += 1
            else:
                user_ans_obj = q.answers.filter(id=chosen_id).first()
                wrong_details.append({
                    "question": q.question_text,
                    "student_chose": user_ans_obj.answer_text if user_ans_obj else "Không chọn",
                    "correct_answer": correct_ans.answer_text if correct_ans else "N/A",
                    "topic": getattr(q.topic, 'title', getattr(q, 'chapter_title', chapter.title)),
                })

        score = round((correct_count / total) * 100, 2) if total > 0 else 0

        # ── Tìm hoặc tạo Quiz đại diện ────────────────────────────────────────
        quiz = Quiz.objects.filter(
            subject=chapter.subject,
            quiz_type='CHAPTER_TEST',
            chapter_coverage__contains=chapter.title
        ).first()

        if not quiz:
            quiz = Quiz.objects.create(
                subject=chapter.subject,
                quiz_type='CHAPTER_TEST',
                title=f"Kiểm tra chương: {chapter.title}",
                passing_score=80,
                chapter_coverage=[chapter.title]
            )

        # ── Lưu QuizSubmission với flag post_test ─────────────────────────────
        submission = QuizSubmission.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            answers_data=answers_data,
            wrong_chapters=[d["topic"] for d in wrong_details],
            passed=(score >= 80)
        )

        # ── Lấy điểm Pre-test từ LearningPath hiện tại ──────────────────────
        pre_test_score = 0.0
        try:
            existing_path = LearningPath.objects.get(user=request.user, chapter=chapter)
            pre_test_score = float(existing_path.pre_test_score or 0)
            # Làm mới timestamp để tránh polling timeout ngay lập tức
            existing_path.status = 'PENDING'
            existing_path.save()
        except LearningPath.DoesNotExist:
            pass

        # ── Kích hoạt AI đánh giá Post-test (bất đồng bộ) ──────────────────
        AIEvaluatorService.trigger_post_test_evaluation(
            user_id=request.user.id,
            subject_id=chapter.subject.id,
            chapter_id=chapter.id,
            chapter_title=chapter.title,
            subject_name=chapter.subject.name,
            grade_level=request.user.grade_level,
            pre_test_score=pre_test_score,
            post_test_score=score,
            wrong_details=wrong_details
        )

        return Response({
            "submission_id": submission.id,
            "score": score,
            "correct_count": correct_count,
            "total_questions": total,
            "passed": score >= 80,
            "message": "AI đang phân tích kết quả và tạo nhận xét cho bạn..."
        }, status=status.HTTP_201_CREATED)


class PostTestResultView(APIView):
    """
    GET /api/quiz/post-test/result/<submission_id>/
    Polling endpoint: Chờ AI chấm xong Post-test và trả kết quả đầy đủ.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, submission_id):
        from django.shortcuts import get_object_or_404
        from apps.curriculum.models import Chapter

        submission = get_object_or_404(QuizSubmission, id=submission_id, user=request.user)

        # Lấy chapter từ chapter_coverage
        chapter_coverage = submission.quiz.chapter_coverage or []
        chapter_title = chapter_coverage[0] if chapter_coverage else None
        chapter = None
        if chapter_title:
            chapter = Chapter.objects.filter(
                subject=submission.quiz.subject,
                title=chapter_title
            ).first()

        # Tìm LearningPath của chương này
        path = None
        if chapter:
            path = LearningPath.objects.filter(
                user=request.user,
                chapter=chapter
            ).first()

        # Chưa có path hoặc chưa có kết quả post-test
        if not path or path.post_test_score is None:
            # Kiểm tra timeout (2 phút)
            import datetime
            now = timezone.now()
            if path and (now - path.updated_at).total_seconds() > 120:
                return Response({
                    "score": float(submission.score),
                    "evaluator_status": "failed",
                    "error_message": "AI analysis timed out.",
                    "learning_path_id": path.id if path else None
                })
            return Response({
                "score": float(submission.score),
                "evaluator_status": "evaluating",
                "learning_path_id": path.id if path else None
            })

        # AI đã hoàn thành → trả kết quả đầy đủ
        questions = Question.objects.filter(
            id__in=submission.answers_data.keys()
        ).prefetch_related('answers')
        q_serializer = QuestionWithAnswerSerializer(questions, many=True)

        next_chapter = None
        if chapter and chapter.order_num is not None:
            next_chapter = Chapter.objects.filter(
                subject=submission.quiz.subject,
                order_num__gt=chapter.order_num
            ).order_by('order_num').first()

        return Response({
            "score": float(submission.score),
            "evaluator_status": "completed",
            "learning_path_id": path.id,
            "pre_test_score": float(path.pre_test_score or 0),
            "post_test_score": float(path.post_test_score),
            "improvement": float(path.post_test_score) - float(path.pre_test_score or 0),
            "subject_id": submission.quiz.subject_id,
            "subject_name": submission.quiz.subject.name,
            "chapter_id": chapter.id if chapter else None,
            "chapter_title": chapter.title if chapter else None,
            "next_chapter_id": next_chapter.id if next_chapter else None,
            "ai_feedback": path.post_test_ai_feedback,
            "questions": q_serializer.data,
            "user_answers": submission.answers_data,
            "correct_count": int(float(submission.score) * questions.count() / 100)
        })


class SeedingStatusView(APIView):
    """
    GET /api/quiz/seeding-status/
    Bao cao tien do nap de thi AI tren toan he thong.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.subjects.models import Subject
        from apps.curriculum.models import Chapter
        from apps.quiz.models import Question
        
        subjects = Subject.objects.all().order_by('grade_level', 'name')
        report = []
        total_questions = Question.objects.count()

        for subj in subjects:
            chapters = Chapter.objects.filter(subject=subj)
            q_count = Question.objects.filter(quiz__subject=subj).count()
            
            target = chapters.count() * 20
            progress = round((q_count / target * 100), 1) if target > 0 else 0

            report.append({
                "subject": subj.name,
                "grade": subj.grade_level,
                "chapters_count": chapters.count(),
                "questions_count": q_count,
                "target_questions": target,
                "progress_percent": progress
            })

        return Response({
            "total_system_questions": total_questions,
            "estimated_completion_time": "4-6 hours",
            "status": "AI Seeding in progress...",
            "details": report
        })
