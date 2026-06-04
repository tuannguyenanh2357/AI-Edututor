from rest_framework import serializers
from .models import Subject, SubjectDocument
from apps.curriculum.models import Part, Chapter, Lesson


class SubjectDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectDocument
        fields = ['id', 'title', 'content', 'pdf_file', 'uploaded_at']


class LessonBriefSerializer(serializers.ModelSerializer):
    """Serializer gọn cho Subject overview (không embed topics)."""
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'lesson_number', 'page_start', 'order_num']


class ChapterBriefSerializer(serializers.ModelSerializer):
    """Serializer gọn cho Subject overview."""
    lessons = LessonBriefSerializer(many=True, read_only=True)
    part_title = serializers.ReadOnlyField(source='part.title')

    class Meta:
        model = Chapter
        fields = ['id', 'chapter_type', 'title', 'chapter_number', 'part_title', 'order_num', 'lessons']


class PartBriefSerializer(serializers.ModelSerializer):
    chapters = ChapterBriefSerializer(many=True, read_only=True)

    class Meta:
        model = Part
        fields = ['id', 'title', 'order_num', 'chapters']


class SubjectSerializer(serializers.ModelSerializer):
    chapters = ChapterBriefSerializer(many=True, read_only=True)
    parts = PartBriefSerializer(many=True, read_only=True)
    documents = SubjectDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'grade_level', 'description',
            'icon_url', 'page_offset',
            'parts', 'chapters', 'documents'
        ]
