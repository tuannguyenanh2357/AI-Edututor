from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PartViewSet, ChapterViewSet, LessonViewSet, TopicViewSet

router = DefaultRouter()
router.register(r'parts', PartViewSet, basename='part')
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'topics', TopicViewSet, basename='topic')

urlpatterns = [
    path('', include(router.urls)),
]
