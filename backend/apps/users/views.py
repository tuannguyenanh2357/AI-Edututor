from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from apps.quiz.models import QuizSubmission
from apps.subjects.models import Subject
from .models import LearningPath, LearningPathItem, LearningProgress
from .serializers import (
    RegisterSerializer, LoginSerializer, CustomUserSerializer, 
    LearningPathSerializer, PasswordResetSerializer, ResetPasswordConfirmSerializer
)
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import os
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Tạo tài khoản thành công!",
            "user": CustomUserSerializer(user).data,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        User = get_user_model()
        user_obj = User.objects.filter(email=email).first()
        if user_obj:
            user = authenticate(username=user_obj.username, password=password)
        else:
            user = None

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Đăng nhập thành công!",
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": CustomUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Email hoặc mật khẩu không chính xác."}, status=status.HTTP_401_UNAUTHORIZED)

class GoogleLoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = request.data.get('idToken')
        if not token:
            return Response({"error": "Không tìm thấy token của Google"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            client_id = settings.GOOGLE_CLIENT_ID
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
            email = idinfo.get('email')
            if not email:
                return Response({"error": "Google không cung cấp email"}, status=status.HTTP_400_BAD_REQUEST)

            User = get_user_model()
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user, created = User.objects.get_or_create(email=email, defaults={
                'username': username,
                'role': 'USER',
                'full_name': idinfo.get('name', ''),
                'avatar_url': idinfo.get('picture', ''),
            })

            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Đăng nhập Google thành công!",
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": CustomUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": f"Token Google không hợp lệ: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({"error": f"Lỗi hệ thống khi đăng nhập Google: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        User = get_user_model()
        user = User.objects.filter(email=email).first()

        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            # Thay đổi URL này thành URL frontend của bạn
            reset_url = f"http://localhost:4200/reset-password?uid={uid}&token={token}"
            
            subject = "Đặt lại mật khẩu cho EduTutor"
            message = f"Xin chào {user.username},\n\nBạn đã yêu cầu đặt lại mật khẩu. Vui lòng nhấp vào liên kết dưới đây để thực hiện:\n{reset_url}\n\nNếu bạn không yêu cầu điều này, vui lòng bỏ qua email này."
            
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
            
        return Response({"message": "Nếu email tồn tại trong hệ thống, chúng tôi đã gửi hướng dẫn đặt lại mật khẩu."}, status=status.HTTP_200_OK)

class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordConfirmSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uidb64 = serializer.validated_data['uidb64']
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            User = get_user_model()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            
        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(password)
            user.save()
            return Response({"message": "Đặt lại mật khẩu thành công!"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn."}, status=status.HTTP_400_BAD_REQUEST)

class UserRoleView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomUserSerializer
    def get_object(self):
        return self.request.user

class UpdateProfileView(APIView):
    """API cập nhật hồ sơ người dùng đầy đủ"""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        data = request.data
        errors = {}

        # Họ và tên
        if 'full_name' in data:
            user.full_name = data['full_name']
            parts = str(data['full_name']).strip().split(' ', 1)
            user.last_name = parts[0]
            user.first_name = parts[1] if len(parts) > 1 else ''

        # Username (kiểm tra trùng)
        if 'username' in data and data['username'] != user.username:
            User = get_user_model()
            if User.objects.filter(username=data['username']).exclude(pk=user.pk).exists():
                errors['username'] = 'Tên đăng nhập này đã tồn tại.'
            else:
                user.username = data['username']

        # Email (kiểm tra trùng)
        if 'email' in data and data['email'] != user.email:
            User = get_user_model()
            if User.objects.filter(email=data['email']).exclude(pk=user.pk).exists():
                errors['email'] = 'Email này đã được sử dụng.'
            else:
                user.email = data['email']

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Các trường khác
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url']
        if 'bio' in data:
            user.bio = data['bio']
        if 'date_of_birth' in data:
            user.date_of_birth = data['date_of_birth'] or None
        if 'grade_level' in data:
            try:
                user.grade_level = int(data['grade_level'])
            except (ValueError, TypeError):
                pass

        user.save()
        return Response(CustomUserSerializer(user).data, status=status.HTTP_200_OK)

class PublicProfileView(APIView):
    """API xem profile công khai theo username"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, username):
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if not user:
            return Response({'error': 'Người dùng không tồn tại'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CustomUserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LogoutView(APIView):
    """Blacklist refresh token khi đăng xuất"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass  # Token đã hết hạn hoặc không hợp lệ, vẫn cho logout
        return Response({'message': 'Đăng xuất thành công'}, status=status.HTTP_200_OK)


class UserProgressView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    def get(self, request):
        student_id = request.query_params.get('student_id')
        subject_name = request.query_params.get('subject')
        
        if not student_id:
            return Response({"error": "Vui lòng cung cấp mã học sinh (student_id)"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Lấy ID chính xác (lesson_id, chapter_id) nếu có — ưu tiên hơn tìm theo tên
        lesson_id = request.query_params.get('lesson_id')
        chapter_id_param = request.query_params.get('chapter_id')
        try: lesson_id = int(lesson_id) if lesson_id else None
        except: lesson_id = None
        try: chapter_id_param = int(chapter_id_param) if chapter_id_param else None
        except: chapter_id_param = None

        # Lấy chapter từ query params và làm sạch (Loại bỏ "Bài 1.", "Chương I.", v.v.)
        import re
        raw_target = self.request.query_params.get('chapter', '')
        target_chapter = re.sub(r'^(Bài|Chương|Topic)\s+\d+[\.\:]\s*', '', raw_target, flags=re.IGNORECASE).strip()
        if not target_chapter: target_chapter = raw_target
        
        # 1. Thống kê điểm số cơ bản
        submissions = QuizSubmission.objects.filter(user_id=student_id)
        if subject_name:
            short_name = subject_name.split()[0]
            submissions = submissions.filter(
                Q(quiz__subject__name__icontains=subject_name) |
                Q(quiz__subject__name__icontains=short_name)
            )
        stats = submissions.aggregate(avg_score=Avg('score'), total_quizzes=Count('id'))
        
        # 2. Lấy thông tin chẩn đoán từ Learning Path (Mastery Map)
        weak_topics = []
        mastered_topics = []
        diagnostic_feedback = ""
        strategy = ""
        
        try:
            # Tìm Learning Path gần nhất của môn học này
            path_query = LearningPath.objects.filter(user_id=student_id).order_by('-id')
            if subject_name:
                # Tìm kiếm linh hoạt hơn: "Toán học" sẽ khớp với "Toán" và ngược lại
                short_name = subject_name.split()[0] if subject_name else ""
                path_query = path_query.filter(
                    Q(subject__name__icontains=subject_name) | 
                    Q(subject__name__icontains=short_name)
                )
            
            path = path_query.first()
            if path:
                strategy = path.strategy
                diagnostic_feedback = path.ai_feedback
                
                # Lấy các phần kiến thức đang ở mức RED, YELLOW hoặc GREEN
                progress_items = LearningProgress.objects.filter(
                    user_id=student_id,
                    learning_path_item__learning_path=path
                ).select_related(
                    'learning_path_item__lesson', 
                    'learning_path_item__lesson__chapter',
                    'learning_path_item__topic', 
                    'learning_path_item__quiz'
                )
                
                for p in progress_items:
                    # Lấy tiêu đề hiển thị
                    title = ""
                    if p.learning_path_item.lesson:
                        title = p.learning_path_item.lesson.title
                    elif p.learning_path_item.topic:
                        title = p.learning_path_item.topic.title
                    elif p.learning_path_item.quiz:
                        title = p.learning_path_item.quiz.title
                    else:
                        title = "N/A"
                    
                    # Lọc theo bài học/chương
                    if lesson_id:
                        # Ưu tiên: lọc chính xác theo lesson_id
                        item_lesson = p.learning_path_item.lesson
                        if not item_lesson or (hasattr(item_lesson, 'id') and item_lesson.id != lesson_id):
                            continue
                    elif chapter_id_param:
                        # Lọc theo chapter_id
                        chapter_obj = None
                        if p.learning_path_item.lesson and p.learning_path_item.lesson.chapter:
                            chapter_obj = p.learning_path_item.lesson.chapter
                        if not chapter_obj or chapter_obj.id != chapter_id_param:
                            continue
                    elif target_chapter:
                        # Fallback: lọc theo tên (cũ)
                        chapter_title = ""
                        if p.learning_path_item.lesson and p.learning_path_item.lesson.chapter:
                            chapter_title = p.learning_path_item.lesson.chapter.title
                        # Chỉ giữ lại nếu tiêu đề khớp chính xác với target_chapter (bài học hiện tại)
                        is_match = (target_chapter.lower() == title.lower())
                        if not is_match:
                            continue

                    if p.mastery_level in ['RED', 'YELLOW']:
                        weak_topics.append({
                            "title": title,
                            "level": p.mastery_level,
                            "errors": p.error_tags or []
                        })
                    elif p.mastery_level == 'GREEN':
                        mastered_topics.append(title)
        except Exception as e:
            print(f"Error fetching path: {e}")

        # 3. Lấy chi tiết các câu làm sai (Wrong Answers History)
        recent_wrong_details = []
        seen_q_ids = set()
        # Không giới hạn số câu sai theo yêu cầu
        max_questions = 1000
        
        try:
            # Lấy toàn bộ các bài thi gần đây
            recent_submissions = submissions.order_by('-submitted_at')
            
            from apps.quiz.models import Question
            from apps.curriculum.models import Chapter, Lesson, Topic

            # Bước 1: xác định set câu hỏi được phép lọc theo lesson_id / chapter_id
            allowed_q_ids = None  # None = không giới hạn (fallback về logic cũ)

            if lesson_id:
                # Trường hợp chính xác nhất: lọc theo lesson_id từ DB
                allowed_q_ids = set(
                    Question.objects.filter(
                        Q(topic__lesson_id=lesson_id) | Q(topic__lesson__id=lesson_id)
                    ).values_list('id', flat=True)
                )
                # Cũng chấp nhận quiz có gắn thẳng với lesson
                lesson_obj = Lesson.objects.filter(id=lesson_id).first()
                if lesson_obj and not target_chapter:
                    import re
                    target_chapter = re.sub(r'^(Bài|Chương|Topic)\s+\d+[\.\:]\s*', '', lesson_obj.title, flags=re.IGNORECASE).strip()
                if not allowed_q_ids:
                    allowed_q_ids = None # Fallback để dùng logic tìm theo tên (target_chapter)
            elif chapter_id_param:
                # Lọc theo chapter_id
                allowed_q_ids = set(
                    Question.objects.filter(
                        Q(topic__lesson__chapter_id=chapter_id_param)
                    ).values_list('id', flat=True)
                )
                chapter_obj = Chapter.objects.filter(id=chapter_id_param).first()
                if chapter_obj and not target_chapter:
                    target_chapter = chapter_obj.title
                if not allowed_q_ids:
                    allowed_q_ids = None # Fallback để dùng logic tìm theo tên (target_chapter)
            
            # Nếu không có ID hoặc phải fallback (allowed_q_ids = None), dùng logic tìm theo tên
            parent_chapter_ids = []
            parent_chapter_titles = []
            if allowed_q_ids is None and target_chapter:
                matched_chapters = Chapter.objects.filter(title__icontains=target_chapter)
                parent_chapter_ids.extend(matched_chapters.values_list('id', flat=True))
                parent_chapter_titles.extend(matched_chapters.values_list('title', flat=True))
                
                matched_lessons = Lesson.objects.filter(title__icontains=target_chapter).select_related('chapter')
                for l in matched_lessons:
                    if l.chapter_id: 
                        parent_chapter_ids.append(l.chapter_id)
                        parent_chapter_titles.append(l.chapter.title)
                
                matched_topics = Topic.objects.filter(title__icontains=target_chapter).select_related('lesson__chapter')
                for t in matched_topics:
                    if t.lesson.chapter_id: 
                        parent_chapter_ids.append(t.lesson.chapter_id)
                        parent_chapter_titles.append(t.lesson.chapter.title)
            
            parent_chapter_titles = list(set(parent_chapter_titles)) # Deduplicate
            
            all_wrong_details = []
            for sub in recent_submissions:
                answers_data = sub.answers_data or {}
                q_ids = [int(qid) for qid in answers_data.keys() if qid.isdigit()]
                
                # Kiểm tra xem Quiz này có liên quan không
                quiz_related = False
                if target_chapter:
                    if target_chapter.lower() in sub.quiz.title.lower():
                        quiz_related = True
                    else:
                        for pt in parent_chapter_titles:
                            if pt.lower() in sub.quiz.title.lower():
                                quiz_related = True
                                break
                
                # Tìm các câu hỏi
                q_query = Question.objects.filter(id__in=q_ids)

                if allowed_q_ids is not None:
                    # Lọc chính xác theo lesson_id / chapter_id (chế độ chính xác)
                    # Cũng cho phép câu hỏi thuộc quiz gắn trực tiếp với lesson/chapter
                    q_query = q_query.filter(id__in=allowed_q_ids)
                elif target_chapter and not quiz_related:
                    # Lọc nghiêm ngặt: Ưu tiên khớp trực tiếp Lesson hoặc Topic trước
                    # Điều này ngăn việc "Mệnh đề" kéo theo "Tập hợp" chỉ vì cùng chương
                    lesson_q = Q(topic__lesson__title__icontains=target_chapter) | Q(topic__title__icontains=target_chapter)
                    
                    # Kiểm tra xem có câu hỏi nào khớp lesson/topic không
                    if q_query.filter(lesson_q).exists():
                        q_query = q_query.filter(lesson_q)
                    else:
                        # Nếu không có câu nào khớp lesson, ta mới mở rộng ra Chapter title hoặc parent_chapter
                        q_query = q_query.filter(
                            Q(chapter_title__icontains=target_chapter) | 
                            Q(topic__lesson__chapter__title__icontains=target_chapter) |
                            Q(topic__lesson__chapter_id__in=parent_chapter_ids) |
                            Q(chapter_title__in=parent_chapter_titles)
                        )
                
                questions = q_query.prefetch_related('answers')
                
                for q in questions:
                    if q.id in seen_q_ids:
                        continue
                        
                    user_ans_id = answers_data.get(str(q.id))
                    correct_ans = q.answers.filter(is_correct=True).first()
                    
                    # Nếu user làm sai
                    if not user_ans_id or (correct_ans and str(user_ans_id) != str(correct_ans.id)):
                        user_ans_obj = q.answers.filter(id=user_ans_id).first() if user_ans_id else None
                        
                        # Xác định mức độ liên quan (Priority)
                        is_match = False
                        if target_chapter:
                            t_lower = target_chapter.lower()
                            lesson_title = (q.lesson_title or (q.topic.lesson.title if q.topic and q.topic.lesson else "")).lower()
                            topic_title = (q.topic.title if q.topic else "").lower()
                            
                            # 1. Khớp mạnh (Strong match): Tên bài học, chủ đề hoặc nội dung câu hỏi
                            if (t_lower in q.question_text.lower() or 
                                t_lower in lesson_title or 
                                t_lower in topic_title):
                                is_match = True
                            # 2. Khớp yếu (Weak match): Chỉ khớp tên chương. Chỉ chấp nhận nếu chưa có lesson/topic rõ ràng khác.
                            elif t_lower in (q.chapter_title or "").lower():
                                # Nếu câu hỏi thuộc về một bài cụ thể KHÁC với target_chapter, thì bỏ qua
                                if lesson_title and t_lower not in lesson_title:
                                    is_match = False
                                else:
                                    is_match = True
                                    # Lọc thủ công dựa trên keyword cho các bài chung chương nếu thiếu lesson_title
                                    if not lesson_title:
                                        q_text_lower = q.question_text.lower()
                                        if "mệnh đề" in t_lower and "tập hợp" in q_text_lower and "mệnh đề" not in q_text_lower:
                                            is_match = False
                                        elif "tập hợp" in t_lower and "mệnh đề" in q_text_lower and "tập hợp" not in q_text_lower:
                                            is_match = False
                                        elif "phương trình" not in t_lower and ("phương trình" in q_text_lower or "bất phương trình" in q_text_lower):
                                            # Nếu bài học hiện tại không liên quan đến phương trình, nhưng câu hỏi có
                                            is_match = False
                                
                        all_wrong_details.append({
                            "question": q.question_text,
                            "user_answer": user_ans_obj.answer_text if user_ans_obj else "Không trả lời",
                            "correct_answer": correct_ans.answer_text if correct_ans else "N/A",
                            "explanation": q.explanation or "",
                            "chapter": q.chapter_title or (q.topic.lesson.chapter.title if q.topic and q.topic.lesson and q.topic.lesson.chapter else "Chung"),
                            "is_match": True if allowed_q_ids is not None else is_match  # Nếu đã lọc theo ID, mọọi câu đều is_match
                        })
                        seen_q_ids.add(q.id)

            # Sắp xếp: Ưu tiên câu khớp bài học đang chọn
            all_wrong_details.sort(key=lambda x: x.get('is_match', False), reverse=True)
            
            # Lọc nghiêm ngặt: Nếu có target_chapter, chỉ lấy những câu CÓ LIÊN QUAN (is_match=True)
            if target_chapter:
                recent_wrong_details = [d for d in all_wrong_details if d.get('is_match')]
                recent_wrong_details = recent_wrong_details[:max_questions]
            else:
                # Nếu không có target, lấy theo thời gian gần nhất (đã có trong list)
                recent_wrong_details = all_wrong_details[:max_questions]
        except Exception as e:
            print(f"Error fetching wrong answers: {e}")

        return Response({
            "progress": {
                "average_score": float(stats.get('avg_score') or 0),
                "total_quizzes": stats.get('total_quizzes') or 0,
                "learning_strategy": strategy,
                "ai_diagnostic": diagnostic_feedback,
                "weak_topics": weak_topics,
                "mastered_topics": mastered_topics,
                "recent_wrong_answers": recent_wrong_details # Lấy tất cả câu sai
            }
        }, status=status.HTTP_200_OK)

# ─── Learning Path APIs ───────────────────────────────────────────────────────

class LearningPathListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        subject_id = request.query_params.get('subject_id')
        qs = LearningPath.objects.filter(user=request.user).exclude(status='PENDING').prefetch_related('items__lesson', 'items__quiz')
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        serializer = LearningPathSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

class LearningPathDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        path = get_object_or_404(LearningPath.objects.filter(user=request.user), id=pk)
        serializer = LearningPathSerializer(path, context={'request': request})
        return Response(serializer.data)

class LearningPathItemCompleteView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        item = get_object_or_404(LearningPathItem, pk=pk)
        if item.learning_path.user != request.user:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        
        progress, _ = LearningProgress.objects.get_or_create(user=request.user, learning_path_item=item)
        progress.status = 'COMPLETED'
        progress.completed_at = timezone.now()
        progress.save()

        next_item = LearningPathItem.objects.filter(learning_path=item.learning_path, order_num=item.order_num + 1).first()
        if next_item:
            next_item.is_unlocked = True
            next_item.save()

        return Response({"status": "ok", "next_item_id": next_item.id if next_item else None})

class LearningProgressStartView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        item = get_object_or_404(LearningPathItem, pk=pk)
        if item.learning_path.user != request.user:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if not item.is_unlocked:
            return Response({"error": "Locked"}, status=status.HTTP_400_BAD_REQUEST)

        progress, _ = LearningProgress.objects.get_or_create(user=request.user, learning_path_item=item)
        if progress.status == 'NOT_STARTED':
            progress.status = 'IN_PROGRESS'
            progress.save()
        return Response({"status": "ok", "progress": progress.status})

class LearningPathResetView(APIView):
    """
    POST /api/users/learning-path/reset/
    Reset lại toàn bộ tiến trình của một lộ trình học (Chapter).
    Dùng cho tính năng "Quay lại học lại" sau khi Post-test không đạt.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        path_id = request.data.get('path_id')
        if not path_id:
            return Response({"error": "Thiếu path_id"}, status=status.HTTP_400_BAD_REQUEST)
            
        path = get_object_or_404(LearningPath, id=path_id, user=request.user)
        
        # 1. Reset tất cả LearningProgress về NOT_STARTED
        items = path.items.all()
        LearningProgress.objects.filter(user=request.user, learning_path_item__in=items).update(
            status='NOT_STARTED',
            completed_at=None,
            score=None
        )
        
        # 2. Khóa tất cả các item ngoại trừ item đầu tiên
        # Sắp xếp theo order_num để đảm bảo lấy đúng bài đầu tiên
        sorted_items = items.order_by('order_num')
        first_item = sorted_items.first()
        
        # Khóa tất cả
        items.update(is_unlocked=False)
        
        # Mở khóa bài đầu tiên
        if first_item:
            first_item.is_unlocked = True
            first_item.save()
            
        # 3. Chuyển trạng thái path về ACTIVE để có thể tiếp tục học
        path.status = 'ACTIVE'
        path.save()
        
        return Response({
            "message": "Lộ trình đã được đặt lại. AI Gia sư đã sẵn sàng để giúp bạn sửa lỗi!",
            "first_item_id": first_item.id if first_item else None
        })
