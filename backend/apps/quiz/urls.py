from django.urls import path
from .views import (
    QuizListView, QuizDetailView, QuizSubmissionView,
    PreTestView, PreTestSubmitView, PreTestResultView,
    ChapterTestView, ChapterTestSubmitView, ChapterTestResultView, SeedingStatusView,
    PostTestSubmitView, PostTestResultView
)

urlpatterns = [
    # Practice quiz
    path('', QuizListView.as_view(), name='quiz-list'),
    path('<int:pk>/', QuizDetailView.as_view(), name='quiz-detail'),
    path('submit/', QuizSubmissionView.as_view(), name='quiz-submit'),

    # Chapter-specific test (= Đánh giá đầu vào theo chương)
    path('chapter-test/', ChapterTestView.as_view(), name='chapter-test'),
    path('chapter-test/submit/', ChapterTestSubmitView.as_view(), name='chapter-test-submit'),
    path('chapter-test/result/<int:submission_id>/', ChapterTestResultView.as_view(), name='chapter-test-result'),
    path('seeding-status/', SeedingStatusView.as_view(), name='seeding-status'),

    # Post-test flow (Final Assessment)
    path('post-test/submit/', PostTestSubmitView.as_view(), name='post-test-submit'),
    path('post-test/result/<int:submission_id>/', PostTestResultView.as_view(), name='post-test-result'),

    # Pre-test flow (New Diagnostic Features)
    path('pre-test/', PreTestView.as_view(), name='pre-test'),
    path('pre-test/submit/', PreTestSubmitView.as_view(), name='pre-test-submit'),
    path('pre-test/result/<int:submission_id>/', PreTestResultView.as_view(), name='pre-test-result'),
]
