import os
from pathlib import Path
from dotenv import load_dotenv

# Thư mục gốc của project (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env từ thư mục gốc của repo (../.env)
load_dotenv(os.path.join(BASE_DIR.parent, '.env'))

# Bảo mật và Debug
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-key-tam-thoi-cho-dev')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*'] # Cho phép mọi IP truy cập trong lúc code (Dev)

# Danh sách các ứng dụng
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Thư viện bên thứ 3
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # Các ứng dụng (App) của nhóm Tuấn
    'apps.users',
    'apps.adminpanel',
    'apps.chat',
    'apps.curriculum',
    'apps.quiz',
    'apps.subjects',
    'apps.gamification',
    'apps.battle',
]

# Middleware xử lý Request
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware', # BẮT BUỘC nằm đây để mở cửa cho Angular
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware', # Đã comment để cho phép Angular load iframe PDF
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# CẤU HÌNH KẾT NỐI DATABASE MYSQL TỪ DOCKER
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'edututor_db'),
        'USER': os.environ.get('DB_USER', 'user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'password'),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES', NAMES 'utf8mb4' COLLATE 'utf8mb4_unicode_ci'",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Ngôn ngữ và Múi giờ
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# File tĩnh (CSS, JS, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================
# CẤU HÌNH CORS (CHO PHÉP ANGULAR GỌI API)
# ==========================================
CORS_ALLOW_ALL_ORIGINS = True # Cho phép mọi nguồn truy cập trong lúc Dev
CORS_ALLOW_CREDENTIALS = True

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'

# ==========================================
# CẤU HÌNH DRF VÀ JWT
# ==========================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# AI Service Configuration
AI_SERVICE_KEY = os.environ.get('AI_SERVICE_KEY', 'dev-ai-key-edututor-2024')
AI_SERVICE_BASE_URL = os.environ.get('AI_SERVICE_URL', 'http://localhost:8001').rstrip('/')
AI_SERVICE_URL = AI_SERVICE_BASE_URL

# Google OAuth2
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

# Gemini API Key
GEMINI_API_KEY = os.environ.get('API_KEY_GEMINI', os.environ.get('APIKEYGEMINI', ''))
GROQ_API_KEY = os.environ.get('API_KEY_GROQ', os.environ.get('APIKEYGROQ', ''))

# ==========================================
# CẤU HÌNH EMAIL (DÙNG CHO QUÊN MẬT KHẨU)
# ==========================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'namanh243848@gmail.com'
EMAIL_HOST_PASSWORD = 'hzho jzks fbey ngbf' 
DEFAULT_FROM_EMAIL = 'EduTutor <namanh243848@gmail.com>'