from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.utils import timezone
from datetime import timedelta
from django.db import connection

from apps.users.models import CustomUser
from apps.quiz.models import Question, Answer, Quiz
from apps.subjects.models import Subject
from apps.curriculum.models import Chapter, Lesson, Topic, Part
import json
import httpx
import sys
import logging
from django.conf import settings

from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

def check_admin(request):
    """Kiểm tra token admin — hỗ trợ JWT hoặc format: 'token-{id}-admin'"""
    header = request.headers.get('Authorization', '')
    if not header:
        return None
    
    try:
        authenticator = JWTAuthentication()
        validated_token = authenticator.get_validated_token(header.replace('Bearer ', '').strip())
        user = authenticator.get_user(validated_token)
        if user and (user.is_superuser or user.is_staff or (hasattr(user, 'role') and user.role in ('ADMIN', 'admin'))):
            return user
    except Exception:
        pass

    token = header.replace('Bearer ', '').strip()
    if 'admin' not in token.lower():
        return None
    try:
        parts = token.split('-')
        user_id = None
        for part in parts:
            if part.isdigit():
                user_id = int(part)
                break
        if user_id is not None:
            user = CustomUser.objects.get(id=user_id)
            if user.is_superuser or user.is_staff or user.role in ('ADMIN', 'admin'):
                return user
    except Exception:
        pass
    
    return None


def execute_query(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return []


SUBJECT_COLORS = {
    'Toán': '#1565c0', 'Vật lý': '#0288d1', 'Lý': '#0288d1', 'Hóa': '#00897b',
    'Lịch sử': '#f57c00', 'Sử': '#f57c00', 'Địa lý': '#7b1fa2', 'Địa': '#7b1fa2',
    'GDCD': '#c62828', 'Giáo dục công dân': '#c62828', 'Sinh học': '#2e7d32', 'Sinh': '#2e7d32',
    'Toán học': '#1565c0', 'Hóa học': '#00897b',
}

def get_subject_color(name):
    for key, color in SUBJECT_COLORS.items():
        if key.lower() in name.lower():
            return color
    return '#1565c0'


@csrf_exempt
@require_GET
def dashboard_stats(request):
    admin = check_admin(request)
    if not admin:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        yesterday_start = today_start - timedelta(days=1)

        res = execute_query("SELECT COUNT(*) as count FROM users WHERE role='USER'")
        total_users = res[0]['count'] if res else 0

        res = execute_query("SELECT COUNT(*) as count FROM users WHERE role='USER' AND created_at >= %s", [week_ago])
        new_users_this_week = res[0]['count'] if res else 0

        res = execute_query("""
            SELECT COUNT(DISTINCT u.id) as count FROM users u
            WHERE u.role='USER' AND (
                EXISTS (SELECT 1 FROM chat_threads ct WHERE ct.user_id=u.id AND ct.created_at >= %s)
                OR EXISTS (SELECT 1 FROM quiz_submissions qs WHERE qs.user_id=u.id AND qs.submitted_at >= %s)
            )
        """, [today_start, today_start])
        active_today = res[0]['count'] if res else 0

        res = execute_query("SELECT COUNT(*) as count FROM users WHERE is_active=0 AND role='USER'")
        locked_accounts = res[0]['count'] if res else 0

        grade_dist = []
        for grade in [10, 11, 12]:
            res = execute_query("SELECT COUNT(*) as count FROM users WHERE grade_level=%s AND role='USER'", [grade])
            grade_dist.append({"label": f"Lớp {grade}", "count": res[0]['count'] if res else 0})

        res = execute_query("SELECT COUNT(*) as count FROM chat_messages WHERE role='user' AND created_at >= %s", [today_start])
        questions_today = res[0]['count'] if res else 0
        res = execute_query("SELECT COUNT(*) as count FROM chat_messages WHERE role='user' AND created_at >= %s AND created_at < %s", [yesterday_start, today_start])
        questions_yesterday = res[0]['count'] if res else 0
        questions_trend = round(((questions_today - questions_yesterday) / questions_yesterday) * 100) if questions_yesterday > 0 else (100 if questions_today > 0 else 0)

        res = execute_query("SELECT COUNT(*) as count FROM quiz_submissions WHERE submitted_at >= %s", [today_start])
        quizzes_today = res[0]['count'] if res else 0
        res = execute_query("SELECT COUNT(*) as count FROM quiz_submissions WHERE submitted_at >= %s AND submitted_at < %s", [yesterday_start, today_start])
        quizzes_yesterday = res[0]['count'] if res else 0
        quizzes_trend = round(((quizzes_today - quizzes_yesterday) / quizzes_yesterday) * 100) if quizzes_yesterday > 0 else (100 if quizzes_today > 0 else 0)

        return JsonResponse({
            "totalUsers": total_users,
            "newUsersThisWeek": new_users_this_week,
            "activeToday": active_today,
            "lockedAccounts": locked_accounts,
            "gradeDistribution": grade_dist,
            "questionsToday": questions_today,
            "questionsTrend": abs(questions_trend),
            "questionsTrendUp": questions_trend >= 0,
            "quizzesToday": quizzes_today,
            "quizzesTrend": abs(quizzes_trend),
            "quizzesTrendUp": quizzes_trend >= 0,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_GET
def subject_stats(request):
    admin = check_admin(request)
    if not admin:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        query = """
            SELECT s.name, COUNT(m.id) as message_count
            FROM subjects s
            LEFT JOIN chat_threads ct ON s.id = ct.subject_id
            LEFT JOIN chat_messages m ON ct.id = m.thread_id
            GROUP BY s.id, s.name
            ORDER BY message_count DESC
        """
        rows = execute_query(query)
        total = sum(r['message_count'] for r in rows) or 1
        result = []
        for row in rows:
            percentage = round((row['message_count'] / total) * 100)
            result.append({
                "name": row['name'],
                "color": get_subject_color(row['name']),
                "percentage": percentage,
                "count": row['message_count'],
            })
        return JsonResponse({"subjects": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_GET
def recent_registrations(request):
    admin = check_admin(request)
    if not admin:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        rows = execute_query("SELECT full_name, email, created_at FROM users WHERE role='USER' ORDER BY created_at DESC LIMIT 10")
        now = timezone.now()
        colors = ['#1565c0', '#00897b', '#f57c00', '#7b1fa2', '#c62828', '#0288d1']
        result = []
        for i, row in enumerate(rows):
            created_at = row['created_at']
            if created_at and not timezone.is_aware(created_at):
                created_at = timezone.make_aware(created_at)
            time_ago = "---"
            if created_at:
                diff = int((now - created_at).total_seconds())
                if diff < 3600: time_ago = f"{diff//60} phút"
                elif diff < 86400: time_ago = f"{diff//3600} giờ"
                else: time_ago = f"{diff//86400} ngày"
            result.append({
                "name": row['full_name'] or row['email'].split('@')[0],
                "email": row['email'],
                "avatarColor": colors[i % len(colors)],
                "timeAgo": time_ago,
            })
        return JsonResponse({"registrations": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_GET
def all_users(request):
    admin = check_admin(request)
    if not admin:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        rows = execute_query("""
            SELECT u.id, u.full_name, u.email, u.role, u.is_active, u.grade_level, u.created_at,
            (
                (SELECT COUNT(*) FROM chat_threads ct WHERE ct.user_id=u.id) +
                (SELECT COUNT(*) FROM quiz_submissions qs WHERE qs.user_id=u.id)
            ) as sessions,
            s.name as current_subject_name, c.title as current_chapter_title
            FROM users u
            LEFT JOIN user_stats us ON us.user_id = u.id
            LEFT JOIN subjects s ON s.id = us.current_subject_id
            LEFT JOIN chapters c ON c.id = us.current_chapter_id
            WHERE u.role='USER'
            ORDER BY u.created_at DESC
        """)
        result = []
        for row in rows:
            result.append({
                "id": row['id'], 
                "name": row['full_name'] or 'User', 
                "email": row['email'],
                "role": row['role'], 
                "grade": row['grade_level'], 
                "totalSessions": row['sessions'],
                "isLocked": not row['is_active'], 
                "createdAt": row['created_at'].strftime('%d/%m/%Y') if row['created_at'] else '',
                "currentSubject": row['current_subject_name'] or 'Chưa chọn',
                "currentChapter": row['current_chapter_title'] or '---'
            })
        return JsonResponse({"users": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def toggle_user_status(request, user_id):
    if request.method != 'POST': return JsonResponse({"error": "Method"}, status=405)
    admin = check_admin(request)
    if not admin: return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        user = CustomUser.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        return JsonResponse({"success": True})
    except: return JsonResponse({"error": "Fail"}, status=500)


@csrf_exempt
@require_GET
def analytics_stats(request):
    admin = check_admin(request)
    if not admin: return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        rows = execute_query("""
            SELECT s.name, s.grade_level, COUNT(ct.id) as sessions
            FROM subjects s LEFT JOIN chat_threads ct ON s.id=ct.subject_id
            GROUP BY s.id, s.name, s.grade_level
        """)
        return JsonResponse({"subjects": rows})
    except Exception as e: return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_GET
def get_question_filters(request):
    admin = check_admin(request)
    if not admin:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    
    subject_name = request.GET.get('subject_name')
    grade = request.GET.get('grade')
    
    try:
        subjects = execute_query("SELECT DISTINCT name, grade_level FROM subjects ORDER BY grade_level, name")
        
        # Lấy theo thứ tự id để giữ đúng trình tự giáo trình (Tập 1 -> Tập 2)
        # 1. Parts
        part_query = "SELECT DISTINCT p.title FROM parts p JOIN subjects s ON p.subject_id = s.id WHERE 1=1"
        p_params = []
        if grade: part_query += " AND s.grade_level = %s"; p_params.append(grade)
        if subject_name: part_query += " AND (s.name = %s OR s.name LIKE %s)"; p_params.extend([subject_name, f"%{subject_name}%"])
        parts_list = [p['title'] for p in execute_query(part_query + " ORDER BY p.id", p_params) if p['title']]

        # 2. Chapters
        chapter_query = "SELECT DISTINCT c.title FROM chapters c JOIN subjects s ON c.subject_id = s.id WHERE 1=1"
        c_params = []
        if grade: chapter_query += " AND s.grade_level = %s"; c_params.append(grade)
        if subject_name: chapter_query += " AND (s.name = %s OR s.name LIKE %s)"; c_params.extend([subject_name, f"%{subject_name}%"])
        chapters_list = [c['title'] for c in execute_query(chapter_query + " ORDER BY c.id", c_params) if c['title']]
        
        # 3. Lessons
        lesson_query = "SELECT DISTINCT l.title FROM lessons l JOIN chapters c ON l.chapter_id = c.id JOIN subjects s ON c.subject_id = s.id WHERE 1=1"
        l_params = []
        if grade: lesson_query += " AND s.grade_level = %s"; l_params.append(grade)
        if subject_name: lesson_query += " AND (s.name = %s OR s.name LIKE %s)"; l_params.extend([subject_name, f"%{subject_name}%"])
        lessons_list = [l['title'] for l in execute_query(lesson_query + " ORDER BY l.id", l_params) if l['title']]

        # Thay vì dùng set() làm mất thứ tự, ta dùng list để giữ trình tự giáo trình
        all_titles = []
        seen = set()
        for t in parts_list + chapters_list + lessons_list:
            if t not in seen:
                all_titles.append(t)
                seen.add(t)

        return JsonResponse({
            "grades": [10, 11, 12],
            "subjects": subjects,
            "chapters": all_titles
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def admin_questions(request):
    admin = check_admin(request)
    if not admin:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == 'GET':
        grade = request.GET.get('grade')
        subject_name = request.GET.get('subject_name')
        chapter_title = request.GET.get('chapter_title')
        search = request.GET.get('search')
        query = "SELECT * FROM questions WHERE 1=1"
        params = []
        if grade: query += " AND grade_level = %s"; params.append(grade)
        if subject_name: query += " AND subject_name = %s"; params.append(subject_name)
        if chapter_title: query += " AND chapter_title LIKE %s"; params.append(f"%{chapter_title}%")
        if search: query += " AND question_text LIKE %s"; params.append(f"%{search}%")
        query += " ORDER BY created_at DESC LIMIT 100"
        rows = execute_query(query, params)
        for row in rows:
            row['answers'] = execute_query("SELECT * FROM answers WHERE question_id = %s", [row['id']])
        return JsonResponse({"questions": rows})

    elif request.method == 'DELETE':
        question_id = request.GET.get('id')
        if not question_id: return JsonResponse({"error": "Missing ID"}, status=400)
        execute_query("DELETE FROM answers WHERE question_id = %s", [question_id])
        execute_query("DELETE FROM questions WHERE id = %s", [question_id])
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Method"}, status=405)


@csrf_exempt
def generate_ai_questions(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method"}, status=405)
    
    admin = check_admin(request)
    if not admin:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        body = json.loads(request.body)
        grade = int(body.get('grade', 10))
        subject_name = body.get('subject_name')
        chapter_title = body.get('chapter_title')
        num_questions = int(body.get('num_questions', 5))

        if not all([subject_name, chapter_title]):
            return JsonResponse({"error": "Thiếu thông tin."}, status=400)

        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            return JsonResponse({"error": "API Key"}, status=500)

        from apps.curriculum.models import Chapter, Lesson, ContentChunk, Part
        from apps.subjects.models import Subject
        from apps.quiz.models import Quiz, Question, Answer
        
        subj_obj = Subject.objects.filter(name__icontains=subject_name, grade_level=grade).first()
        if not subj_obj:
            subj_obj = Subject.objects.filter(grade_level=grade).first() or Subject.objects.first()

        context_content = ""
        meta = {
            'part_title': None,
            'chapter_title': None,
            'chapter_type': 'CHAPTER',
            'lesson_title': None,
            'lesson_number': None,
            'topic_obj': None
        }

        lesson_obj = Lesson.objects.filter(title__icontains=chapter_title, chapter__subject=subj_obj).first()
        if lesson_obj:
            meta['lesson_title'] = lesson_obj.title
            meta['lesson_number'] = lesson_obj.lesson_number
            meta['chapter_title'] = lesson_obj.chapter.title
            meta['chapter_type'] = lesson_obj.chapter.chapter_type
            if lesson_obj.chapter.part:
                meta['part_title'] = lesson_obj.chapter.part.title
            meta['topic_obj'] = lesson_obj.topics.first()

            chunks = ContentChunk.objects.filter(topic__lesson=lesson_obj).only('raw_content')[:15]
            context_content = "\n".join([c.raw_content[:500] for c in chunks if c.raw_content])
        
        if not context_content:
            chapter_obj = Chapter.objects.filter(title__icontains=chapter_title, subject=subj_obj).first()
            if chapter_obj:
                meta['chapter_title'] = chapter_obj.title
                meta['chapter_type'] = chapter_obj.chapter_type
                if chapter_obj.part:
                    meta['part_title'] = chapter_obj.part.title
                
                first_lesson = chapter_obj.lessons.first()
                if first_lesson:
                    meta['lesson_title'] = first_lesson.title
                    meta['lesson_number'] = first_lesson.lesson_number
                    meta['topic_obj'] = first_lesson.topics.first()

                chunks = ContentChunk.objects.filter(topic__lesson__chapter=chapter_obj).only('raw_content')[:15]
                context_content = "\n".join([c.raw_content[:500] for c in chunks if c.raw_content])

        if not context_content:
            part_obj = Part.objects.filter(title__icontains=chapter_title, subject=subj_obj).first()
            if part_obj:
                meta['part_title'] = part_obj.title
                first_chapter = part_obj.chapters.first()
                if first_chapter:
                    meta['chapter_title'] = first_chapter.title
                    meta['chapter_type'] = first_chapter.chapter_type
                    first_lesson = first_chapter.lessons.first()
                    if first_lesson:
                        meta['lesson_title'] = first_lesson.title
                        meta['topic_obj'] = first_lesson.topics.first()

                chunks = ContentChunk.objects.filter(topic__lesson__chapter__part=part_obj).only('raw_content')[:15]
                context_content = "\n".join([c.raw_content[:500] for c in chunks if c.raw_content])

        prompt = f"""Bạn là chuyên gia soạn đề lớp {grade}. Hãy tạo {num_questions} câu hỏi cho: {subject_name}, {chapter_title}.
Nội dung: {context_content[:3000] if context_content else "Kiến thức chuẩn GDPT."}
JSON: {{"questions": [{{ "question_text": "...", "answers": [{{ "text": "...", "is_correct": true }}, ...], "explanation": "...", "bloom_level": 1 }}]}}
"""

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": "Output valid JSON object."}, {"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.5
        }

        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            ai_text = resp.json()['choices'][0]['message']['content']

        try:
            parsed = json.loads(ai_text)
            if isinstance(parsed, list): questions_data = parsed
            elif isinstance(parsed, dict):
                list_key = next((k for k, v in parsed.items() if isinstance(v, list)), None)
                questions_data = parsed[list_key] if list_key else [parsed]
            else: questions_data = []
        except: return JsonResponse({"error": "Lỗi AI"}, status=500)

        quiz_obj, _ = Quiz.objects.get_or_create(
            subject=subj_obj,
            quiz_type='PRACTICE',
            title=f"AI - {chapter_title}",
            defaults={'passing_score': 70}
        )

        saved_count = 0
        for q in questions_data[:num_questions]:
            try:
                txt = q.get('question_text') or q.get('question') or q.get('text')
                if not txt: continue
                
                bloom = int(q.get('bloom_level', 1))
                q_obj = Question.objects.create(
                    quiz=quiz_obj,
                    topic=meta['topic_obj'],
                    question_text=txt,
                    explanation=q.get('explanation', ''),
                    bloom_level=bloom,
                    difficulty_level=bloom,
                    subject_name=subj_obj.name,
                    grade_level=grade,
                    part_title=meta['part_title'],
                    chapter_title=meta['chapter_title'] or chapter_title,
                    chapter_type=meta['chapter_type'],
                    lesson_title=meta['lesson_title'],
                    lesson_number=meta['lesson_number']
                )
                
                ans_list = q.get('answers') or q.get('options') or []
                for a in ans_list:
                    a_txt = a.get('text') or a.get('content') or (a if isinstance(a, str) else '')
                    if a_txt:
                        Answer.objects.create(question=q_obj, answer_text=a_txt, is_correct=a.get('is_correct', False))
                saved_count += 1
            except Exception as e:
                sys.stderr.write(f"Save Error: {str(e)}\n")
                continue

        return JsonResponse({"success": True, "message": f"Đã tạo {saved_count} câu hỏi thành công."})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)