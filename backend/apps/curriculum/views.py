from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Part, Chapter, Lesson, Topic
from .serializers import PartSerializer, ChapterSerializer, LessonSerializer, TopicSerializer


class PartViewSet(viewsets.ReadOnlyModelViewSet):
    """API: Danh sách Phần/Khối (cấp cao nhất - nếu có)."""
    queryset = Part.objects.all().order_by('order_num')
    serializer_class = PartSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Part.objects.all().order_by('order_num')
        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        return qs


class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    """API: Danh sách Chương/Chủ đề."""
    queryset = Chapter.objects.select_related('part').prefetch_related('lessons').order_by('order_num')
    serializer_class = ChapterSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Chapter.objects.select_related('part').prefetch_related(
            'lessons', 'lessons__topics'
        ).order_by('order_num')
        subject_id = self.request.query_params.get('subject_id')
        part_id = self.request.query_params.get('part_id')
        chapter_type = self.request.query_params.get('chapter_type')  # CHAPTER | THEME
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        if part_id:
            qs = qs.filter(part_id=part_id)
        if chapter_type:
            qs = qs.filter(chapter_type=chapter_type)
        return qs


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    """API: Danh sách Bài học."""
    queryset = Lesson.objects.select_related('chapter').order_by('order_num')
    serializer_class = LessonSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Lesson.objects.select_related('chapter__subject', 'chapter__part').prefetch_related(
            'topics'
        ).order_by('order_num')
        chapter_id = self.request.query_params.get('chapter_id')
        subject_id = self.request.query_params.get('subject_id')
        if chapter_id:
            qs = qs.filter(chapter_id=chapter_id)
        if subject_id:
            qs = qs.filter(chapter__subject_id=subject_id)
        return qs


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    """API: Danh sách Chủ đề nhỏ bên trong Bài học."""
    queryset = Topic.objects.select_related('lesson').order_by('order_num')
    serializer_class = TopicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Topic.objects.select_related('lesson__chapter__subject').order_by('order_num')
        lesson_id = self.request.query_params.get('lesson_id')
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        return qs
