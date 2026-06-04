from django.urls import path
from .views import (
    RegisterView, LoginView, GoogleLoginView, UserRoleView, UserProgressView,
    LearningPathListView, LearningPathDetailView, LearningPathItemCompleteView, LearningProgressStartView,
    ForgotPasswordView, ResetPasswordView, UpdateProfileView, LogoutView, PublicProfileView,
    LearningPathResetView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Auth
    path('register', RegisterView.as_view(), name='register'),
    path('login', LoginView.as_view(), name='login'),
    path('google', GoogleLoginView.as_view(), name='google'),
    path('forgot-password', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password', ResetPasswordView.as_view(), name='reset_password'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('me', UserRoleView.as_view(), name='user_me'),
    path('me/update', UpdateProfileView.as_view(), name='update_profile'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('profile/<str:username>', PublicProfileView.as_view(), name='public_profile'),
    path('progress', UserProgressView.as_view(), name='user_progress'),

    # Learning Path (New Diagnostic Features)
    path('learning-path/', LearningPathListView.as_view(), name='learning-path-list'),
    path('learning-path/<int:pk>/', LearningPathDetailView.as_view(), name='learning-path-detail'),
    path('learning-path/items/<int:pk>/start/', LearningProgressStartView.as_view(), name='learning-path-item-start'),
    path('learning-path/items/<int:pk>/complete/', LearningPathItemCompleteView.as_view(), name='learning-path-item-complete'),
    path('learning-path/reset/', LearningPathResetView.as_view(), name='learning-path-reset'),
]
