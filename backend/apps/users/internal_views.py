import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
import json
import traceback

INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "internal-service-key-2024")


def _check_internal_key(request):
    key = request.headers.get("X-Internal-Key", "")
    return key == INTERNAL_API_KEY


@csrf_exempt
@require_POST
def create_learning_path(request):
    """
    POST /api/internal/create-learning-path/
    Nhận data từ AI Evaluator → tạo LearningPath + LearningPathItems.

    Body:
    {
        "user_id": 1,
        "subject_id": 2,
        "score": 65.0,
        "strategy": "standard",
        "ai_feedback": "...",
        "wrong_chapters": ["Hàm số bậc hai", "Đạo hàm"]
    }
    """
    if not _check_internal_key(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_id = data.get("user_id")
    subject_id = data.get("subject_id")
    score = data.get("score", 0)
    strategy = data.get("strategy", "standard")
    ai_feedback = data.get("ai_feedback", "")
    wrong_chapters = data.get("wrong_chapters", [])
    mastery_map = data.get("mastery_map", {})
    error_tags = data.get("error_tags", [])

    if not user_id or not subject_id:
        return JsonResponse({"error": "user_id và subject_id là bắt buộc."}, status=400)

    from apps.users.models import LearningPath, LearningPathItem, CustomUser
    from apps.subjects.models import Subject
    from apps.curriculum.models import Chapter, Lesson
    from apps.quiz.models import Quiz

    try:
        user = CustomUser.objects.get(id=user_id)
        subject = Subject.objects.get(id=subject_id)
    except (CustomUser.DoesNotExist, Subject.DoesNotExist) as e:
        return JsonResponse({"error": str(e)}, status=404)

    import traceback
    try:
        # ── Tạo hoặc cập nhật LearningPath ───────────────────────────────────────
        path, created = LearningPath.objects.get_or_create(
            user=user,
            subject=subject,
            defaults={
                "pre_test_score": score,
                "strategy": strategy,
                "ai_feedback": ai_feedback,
                "status": "ACTIVE",
            }
        )

        if not created:
            path.pre_test_score = score
            path.strategy = strategy
            path.ai_feedback = ai_feedback
            path.status = "ACTIVE"
            path.save()
            path.items.all().delete()

        # ── Tầng xử lý logic Precision Learning ──────────────────────────────
        order = 0
        items_created = 0
        all_chapters = Chapter.objects.filter(subject=subject).order_by('order_num')

        from apps.users.models import LearningProgress

        for chapter in all_chapters:
            # Lấy mức độ thông thạo từ AI (Fuzzy matching)
            m_level = "RED" # Mặc định là cần học nếu không có trong map
            ch_title_lower = chapter.title.lower()
            for ai_ch, ai_level in mastery_map.items():
                if ai_ch.lower() in ch_title_lower or ch_title_lower in ai_ch.lower():
                    m_level = ai_level
                    break

            # Tạo nội dung cho chương (không bỏ qua chương GREEN để học sinh thấy roadmap đầy đủ)
            lessons = Lesson.objects.filter(chapter=chapter).order_by('order_num')
            for lesson in lessons:
                # Tạo Item: Nếu RED thì học cả bài (LESSON), nếu YELLOW thì chỉ học Topic cụ thể
                item_type = 'LESSON' if (m_level == "RED") else 'TOPIC'
                path_item = LearningPathItem.objects.create(
                    learning_path=path,
                    item_type=item_type,
                    lesson=lesson if item_type == 'LESSON' else None,
                    topic=lesson.topics.first() if item_type == 'TOPIC' else None,
                    order_num=order,
                    is_unlocked=(order == 0),
                )
                
                # Tạo record Progress
                status = 'COMPLETED' if m_level == 'GREEN' else 'PENDING'
                LearningProgress.objects.create(
                    user=user,
                    learning_path_item=path_item,
                    mastery_level=m_level,
                    status=status,
                    completed_at=timezone.now() if status == 'COMPLETED' else None,
                    error_tags=error_tags if m_level == "RED" else []
                )
                order += 1
                items_created += 1

            # Thêm quiz cho chương
            post_quizzes = Quiz.objects.filter(subject=subject, quiz_type='POST_TEST')
            post_quiz = None
            for q in post_quizzes:
                coverage = q.chapter_coverage
                if isinstance(coverage, list) and chapter.title in coverage:
                    post_quiz = q
                    break

            if post_quiz:
                path_item = LearningPathItem.objects.create(
                    learning_path=path,
                    item_type='QUIZ',
                    quiz=post_quiz,
                    order_num=order,
                    is_unlocked=False,
                )
                LearningProgress.objects.create(
                    user=user,
                    learning_path_item=path_item,
                    mastery_level=m_level
                )
                order += 1
                items_created += 1

        if items_created == 0:
            print(f"⚠️ [Internal] Không tìm thấy content để tạo items cho subject {subject_id}.")
            print(f"Note: No content found to create items for subject {subject_id}.")

        print(f"[Internal] LearningPath #{path.id} created {items_created} items for user {user_id} ({strategy})")

        return JsonResponse({
            "status": "ok",
            "learning_path_id": path.id,
            "items_created": items_created,
            "strategy": strategy,
        })

    except Exception as e:
        print(f"!!! [Internal Error] {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_POST
def create_chapter_learning_path(request):
    """
    POST /api/internal/create-chapter-learning-path/
    Nhận data từ AI Evaluator (chapter-based) → tạo LearningPath + Items cho chương.
    """
    if not _check_internal_key(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_id = data.get("user_id")
    subject_id = data.get("subject_id")
    chapter_id = data.get("chapter_id")
    score = data.get("score", 0)
    strategy = data.get("strategy", "standard")
    ai_feedback = data.get("ai_feedback", "")
    mastery_map = data.get("mastery_map", {})

    if not user_id or not chapter_id:
        return JsonResponse({"error": "user_id và chapter_id là bắt buộc."}, status=400)

    from apps.users.models import LearningPath, LearningPathItem, LearningProgress, CustomUser
    from apps.subjects.models import Subject
    from apps.curriculum.models import Chapter, Lesson

    try:
        user = CustomUser.objects.get(id=user_id)
        chapter = Chapter.objects.select_related('subject').get(id=chapter_id)
    except (CustomUser.DoesNotExist, Chapter.DoesNotExist) as e:
        return JsonResponse({"error": str(e)}, status=404)

    import traceback
    try:
        # Tìm hoặc tạo LearningPath per CHAPTER
        path, created = LearningPath.objects.get_or_create(
            user=user,
            chapter=chapter,
            defaults={
                "subject": chapter.subject,
                "pre_test_score": score,
                "strategy": strategy,
                "ai_feedback": ai_feedback,
                "status": "ACTIVE",
            }
        )

        if not created and path.status == 'ACTIVE':
            # NẾU ĐÃ TỒN TẠI VÀ ĐANG ACTIVE -> Đây là kết quả của bài Test Đầu Ra (Post-Test)
            # Sau khi làm xong bài test đầu ra của một chương đang học, ta đánh dấu hoàn thành.
            path.status = 'COMPLETED'
            path.save()
            
            # Unlock next chapter
            next_chapter = None
            if chapter.order_num is not None:
                next_chapter = Chapter.objects.filter(
                    subject=chapter.subject, 
                    order_num__gt=chapter.order_num
                ).order_by('order_num').first()
            
            if next_chapter:
                LearningPath.objects.get_or_create(
                    user=user,
                    chapter=next_chapter,
                    defaults={"subject": chapter.subject, "status": "LOCKED"}
                )
            
            return JsonResponse({
                "status": "ok",
                "learning_path_id": path.id,
                "items_created": 0,
                "message": "Đã hoàn thành chương"
            })

        if not created and path.status == 'PENDING':
            # Cập nhật thông tin từ AI cho bản ghi PENDING
            path.pre_test_score = score
            path.strategy = strategy
            path.ai_feedback = ai_feedback
            path.status = 'ACTIVE'
            path.save()
            # Tiếp tục xuống dưới để tạo items

        # Tạo items từ các bài học trong chương
        order = 0
        items_created = 0
        lessons = Lesson.objects.filter(chapter=chapter).order_by('order_num')
        
        # Mastery logic: Nếu >= 80% thì Mastered All (Skip)
        is_mastered_all = (score >= 80)

        for lesson in lessons:
            # Ưu tiên lấy từ mastery_map (AI chẩn đoán)
            m_level = "GREEN" if is_mastered_all else "PENDING"
            specific_errors = []
            
            lesson_title_lower = lesson.title.lower()
            found_in_map = False
            for ai_key, ai_val in mastery_map.items():
                if ai_key.lower() in lesson_title_lower or lesson_title_lower in ai_key.lower():
                    if isinstance(ai_val, dict):
                        m_level = ai_val.get("level", "GREEN")
                        specific_errors = ai_val.get("specific_errors", [])
                    else:
                        m_level = str(ai_val)
                    found_in_map = True
                    break
            
            # Nếu không có trong map và không phải trường hợp Mastered All -> Mặc định là RED (cần học)
            if not found_in_map and not is_mastered_all:
                m_level = "RED"

            item_type = 'LESSON'
            path_item = LearningPathItem.objects.create(
                learning_path=path,
                item_type=item_type,
                lesson=lesson,
                topic=None,
                order_num=order,
                is_unlocked=True if (is_mastered_all or order == 0) else False,
            )
            
            # Status determination
            status = 'COMPLETED' if (is_mastered_all or m_level == 'GREEN') else 'PENDING'
            
            LearningProgress.objects.create(
                user=user,
                learning_path_item=path_item,
                mastery_level=m_level,
                status=status,
                completed_at=timezone.now() if status == 'COMPLETED' else None,
                error_tags=specific_errors if m_level in ['RED', 'YELLOW'] else []
            )
            order += 1
            items_created += 1

        # [MỚI] Nếu Mastered hết chương, đánh dấu hoàn thành và mở khóa chương tiếp theo (nếu có)
        if is_mastered_all:
            path.status = 'COMPLETED'
            path.save()
            
            next_chapter = None
            if chapter.order_num is not None:
                next_chapter = Chapter.objects.filter(
                    subject=chapter.subject, 
                    order_num__gt=chapter.order_num
                ).order_by('order_num').first()
            
            if next_chapter:
                # Tạo một LearningPath rỗng hoặc PENDING cho chương tiếp theo để Frontend hiển thị "Mở khóa"
                LearningPath.objects.get_or_create(
                    user=user,
                    chapter=next_chapter,
                    defaults={"subject": chapter.subject, "status": "LOCKED"}
                )

        print(f"[Internal] Chapter LearningPath #{path.id} created {items_created} items (chapter={chapter_id}, user={user_id})")

        return JsonResponse({
            "status": "ok",
            "learning_path_id": path.id,
            "items_created": items_created,
        })

    except Exception as e:
        print(f"!!! [Internal Error - Chapter Path] {str(e)}")
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def get_learning_path_progress(request):
    """
    GET /api/internal/learning-path/progress/?user_id=1&subject_id=2
    """
    if not _check_internal_key(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user_id = request.GET.get("user_id")
    subject_id = request.GET.get("subject_id")

    if not user_id or not subject_id:
        return JsonResponse({"error": "missing params"}, status=400)

    from apps.users.models import LearningPath, LearningProgress
    from apps.users.serializers import LearningPathSerializer

    try:
        path = LearningPath.objects.prefetch_related('items__lesson', 'items__quiz').get(
            user_id=user_id, subject_id=subject_id
        )
        # Use existing serializer to get items and their status
        # We need to pass mock request or manually handle it since we are in internal view
        data = LearningPathSerializer(path, context={'request': type('obj', (object,), {'user': path.user})}).data
        return JsonResponse(data)
    except LearningPath.DoesNotExist:
        return JsonResponse({"error": "Path not found"}, status=404)


@csrf_exempt
def get_pretest_results(request):
    """
    GET /api/internal/learning-path/pre-test-results/?user_id=1&subject_id=2
    Lấy chi tiết bài pre-test cuối cùng của user cho môn học này.
    """
    if not _check_internal_key(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user_id = request.GET.get("user_id")
    subject_id = request.GET.get("subject_id")

    if not user_id or not subject_id:
        return JsonResponse({"error": "missing params"}, status=400)

    from apps.quiz.models import QuizSubmission, Question
    from apps.quiz.serializers import QuestionWithAnswerSerializer

    try:
        # Tìm submission gần nhất của Pre-test môn này
        submission = QuizSubmission.objects.filter(
            user_id=user_id,
            quiz__subject_id=subject_id,
            quiz__quiz_type='PRE_TEST'
        ).order_by('-submitted_at').first()

        if not submission:
            return JsonResponse({"error": "No pre-test submission found"}, status=404)

        questions = submission.quiz.questions.prefetch_related('answers').all()
        q_data = QuestionWithAnswerSerializer(questions, many=True).data

        return JsonResponse({
            "score": float(submission.score or 0),
            "submitted_at": submission.submitted_at,
            "user_answers": submission.answers_data,
            "wrong_chapters": submission.wrong_chapters,
            "questions": q_data
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def update_item_status(request):
    """
    POST /api/internal/learning-path/item/complete/
    Body: {"user_id": 1, "item_id": 10}
    """
    if not _check_internal_key(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        item_id = data.get("item_id")
        
        from apps.users.models import LearningPathItem, LearningProgress, CustomUser
        from django.utils import timezone

        item = LearningPathItem.objects.get(id=item_id)
        user = CustomUser.objects.get(id=user_id)

        progress, _ = LearningProgress.objects.get_or_create(user=user, learning_path_item=item)
        progress.status = 'COMPLETED'
        progress.completed_at = timezone.now()
        progress.save()

        # Unlock next
        next_item = LearningPathItem.objects.filter(
            learning_path=item.learning_path,
            order_num=item.order_num + 1
        ).first()
        if next_item:
            next_item.is_unlocked = True
            next_item.save()

        return JsonResponse({"status": "ok", "next_item_id": next_item.id if next_item else None})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def save_post_test_result(request):
    """
    POST /api/internal/save-post-test-result/
    Nhận kết quả chấm bài Post-test từ AI Service và lưu vào LearningPath.

    Body:
    {
        "user_id": 1,
        "chapter_id": 5,
        "post_test_score": 85.0,
        "post_test_ai_feedback": "Nhận xét của AI..."
    }
    """
    if not _check_internal_key(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_id = data.get("user_id")
    chapter_id = data.get("chapter_id")
    post_test_score = data.get("post_test_score", 0)
    post_test_ai_feedback = data.get("post_test_ai_feedback", "")

    if not user_id or not chapter_id:
        return JsonResponse({"error": "user_id và chapter_id là bắt buộc."}, status=400)

    from apps.users.models import LearningPath

    try:
        path = LearningPath.objects.get(user_id=user_id, chapter_id=chapter_id)
        path.post_test_score = post_test_score
        path.post_test_ai_feedback = post_test_ai_feedback
        path.status = 'COMPLETED'
        path.save()

        print(f"[Internal] Post-test saved: Path #{path.id}, score={post_test_score:.1f}%, user={user_id}")
        return JsonResponse({
            "status": "ok",
            "learning_path_id": path.id,
            "post_test_score": post_test_score
        })
    except LearningPath.DoesNotExist:
        return JsonResponse({"error": f"Không tìm thấy LearningPath cho user={user_id}, chapter={chapter_id}"}, status=404)
    except Exception as e:
        print(f"!!! [save_post_test_result Error] {str(e)}")
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
