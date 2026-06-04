from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
import json

# 1. API ĐĂNG KÝ
@csrf_exempt
def register_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '')
            password = data.get('password', '')
            full_name = data.get('fullName', '')

            if User.objects.filter(email=email).exists():
                return JsonResponse({"error": "Email đã tồn tại"}, status=400)

            username = email.split('@')[0]
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name
            )
            return JsonResponse({
                "message": "Tạo tài khoản thành công cho " + full_name,
                "status": "success"
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"message": "Chỉ nhận POST"}, status=405)


# API ĐĂNG NHẬP (có phân quyền)
@csrf_exempt
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '')
            password = data.get('password', '')

            print(f"Nhận được yêu cầu Đăng Nhập từ email: {email}")

            # Tìm user theo email
            try:
                user_obj = User.objects.get(email=email)
                username = user_obj.username
            except User.DoesNotExist:
                return JsonResponse({"error": "Email không tồn tại"}, status=401)

            # Xác thực password
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Xác định role
                if user.is_superuser or user.is_staff:
                    role = 'admin'
                else:
                    role = 'user'

                return JsonResponse({
                    "message": "Đăng nhập thành công!",
                    "access_token": f"token-{user.id}-{role}",
                    "role": role,
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.get_full_name() or user.username,
                        "is_admin": user.is_superuser or user.is_staff
                    }
                }, status=200)
            else:
                return JsonResponse({"error": "Mật khẩu không chính xác"}, status=401)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"message": "Chỉ nhận POST"}, status=405)

# 3. DANH SÁCH ĐƯỜNG DẪN
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/chat/', include('apps.chat.urls')),
    path('api/subjects/', include('apps.subjects.urls')),
    path('api/curriculum/', include('apps.curriculum.urls')),
    path('api/quiz/', include('apps.quiz.urls')),
    path('api/gamification/', include('apps.gamification.urls')),
    path('api/battle/', include('apps.battle.urls')),
    path('api/internal/', include('apps.users.internal_urls')),
    path('api/admin/', include('apps.adminpanel.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)