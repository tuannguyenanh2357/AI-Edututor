from django.urls import path
from . import views

urlpatterns = [
    path('stats/', views.dashboard_stats, name='admin_dashboard_stats'),
    path('subjects/', views.subject_stats, name='admin_subject_stats'),
    path('registrations/', views.recent_registrations, name='admin_recent_registrations'),
    path('users/', views.all_users, name='admin_all_users'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='admin_toggle_user_status'),
    path('analytics/', views.analytics_stats, name='admin_analytics_stats'),
    
    # Question Management
    path('questions/', views.admin_questions, name='admin_questions'),
    path('questions/filters/', views.get_question_filters, name='admin_get_question_filters'),
    path('questions/generate-ai/', views.generate_ai_questions, name='admin_generate_ai_questions'),
]
