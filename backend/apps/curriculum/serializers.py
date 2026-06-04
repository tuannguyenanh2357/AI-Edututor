from rest_framework import serializers
from .models import Part, Chapter, Lesson, Topic


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'title', 'content', 'order_num']


class LessonSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True)
    subject_id = serializers.ReadOnlyField(source='chapter.subject.id')
    chapter_id = serializers.ReadOnlyField(source='chapter.id')

    class Meta:
        model = Lesson
        fields = [
            'id', 'chapter_id', 'subject_id',
            'title', 'lesson_number',
            'page_start', 'page_end', 'content',
            'order_num', 'created_at',
            'topics',
        ]


class ChapterSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    part_title = serializers.ReadOnlyField(source='part.title')
    has_learning_path = serializers.SerializerMethodField()
    learning_path_id = serializers.SerializerMethodField()
    is_mastered = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = [
            'id', 'subject', 'part', 'part_title',
            'chapter_type', 'title', 'chapter_number',
            'description', 'order_num', 'created_at',
            'lessons',
            'has_learning_path', 'learning_path_id', 'is_mastered', 'is_completed',
        ]

    def get_has_learning_path(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return False
        from apps.users.models import LearningPath
        return LearningPath.objects.filter(user=user, chapter=obj).exclude(status='LOCKED').exists()

    def get_learning_path_id(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return None
        from apps.users.models import LearningPath
        lp = LearningPath.objects.filter(user=user, chapter=obj).exclude(status='LOCKED').first()
        return lp.id if lp else None

    def get_is_mastered(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return False
        from apps.users.models import LearningPath
        lp = LearningPath.objects.filter(user=user, chapter=obj, status='COMPLETED').first()
        if not lp:
            return False
        
        # Tinh thông khi có điểm >= 80 ở pre_test hoặc post_test
        pre_score = float(lp.pre_test_score or 0)
        post_score = float(lp.post_test_score or 0)
        return pre_score >= 80 or post_score >= 80

    def get_is_completed(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return False
        from apps.users.models import LearningPath
        return LearningPath.objects.filter(user=user, chapter=obj, status='COMPLETED').exists()


class PartSerializer(serializers.ModelSerializer):
    """Phần/Khối - cấp cao nhất (nếu có)."""
    chapters = ChapterSerializer(many=True, read_only=True)

    class Meta:
        model = Part
        fields = ['id', 'subject', 'title', 'order_num', 'chapters']
