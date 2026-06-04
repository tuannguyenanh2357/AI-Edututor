from rest_framework import serializers
from .models import CustomUser, LearningPath, LearningPathItem
from django.contrib.auth import authenticate

class CustomUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'role', 'rank',
            'total_xp', 'grade_level', 'avatar_url', 'full_name',
            'bio', 'date_of_birth', 'current_streak', 'max_streak', 'gems', 'created_at'
        )
        read_only_fields = ('id', 'role', 'rank', 'total_xp', 'gems', 'current_streak', 'max_streak')

    def get_role(self, obj):
        # Nếu là superuser hoặc staff thì luôn trả về ADMIN để frontend cho phép vào Dashboard
        if obj.is_superuser or obj.is_staff:
            return 'ADMIN'
        return obj.role

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'full_name', 'grade_level']
        extra_kwargs = {
            'username': {'required': False},
            'full_name': {'required': False},
        }
    
    def create(self, validated_data):
        # Tự sinh username từ email nếu để trống
        if not validated_data.get('username'):
            email = validated_data.get('email')
            base_username = email.split('@')[0]
            validated_data['username'] = base_username
            
        # Đảm bảo username duy nhất
        base_user = validated_data['username']
        counter = 1
        while CustomUser.objects.filter(username=validated_data['username']).exists():
            validated_data['username'] = f"{base_user}{counter}"
            counter += 1
            
        user = CustomUser.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            try:
                # Tìm user trực tiếp bằng email
                user = CustomUser.objects.get(email=email)
                
                # Kiểm tra mật khẩu thủ công (an toàn hơn cho CustomUser)
                if not user.check_password(password):
                    raise serializers.ValidationError("Mật khẩu không chính xác.")
                
                if not user.is_active:
                    raise serializers.ValidationError("Tài khoản này đã bị khóa.")
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("Email không tồn tại.")
        else:
            raise serializers.ValidationError("Phải cung cấp cả email và mật khẩu.")

        data['user'] = user
        return data

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6, write_only=True)
    token = serializers.CharField()
    uidb64 = serializers.CharField()

# ─── Learning Path Serializers ───────────────────────────────────────────────

class LearningPathItemSerializer(serializers.ModelSerializer):
    chapter_name = serializers.SerializerMethodField()
    chapter_id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    mastery_level = serializers.SerializerMethodField()
    
    lesson_id = serializers.IntegerField(source='lesson.id', read_only=True, default=None)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True, default='')
    lesson_number = serializers.SerializerMethodField()
    quiz_title = serializers.CharField(source='quiz.title', read_only=True, default='')
    error_tags = serializers.SerializerMethodField()
    topics_list = serializers.SerializerMethodField()
    
    class Meta:
        model = LearningPathItem
        fields = ['id', 'item_type', 'lesson_id', 'lesson_title', 'lesson_number', 'quiz_title', 'status', 'order_num', 'is_unlocked', 'chapter_name', 'chapter_id', 'mastery_level', 'error_tags', 'topics_list']

    def get_chapter_name(self, obj):
        if obj.lesson and obj.lesson.chapter:
            return obj.lesson.chapter.title
        if obj.topic and obj.topic.lesson and obj.topic.lesson.chapter:
            return obj.topic.lesson.chapter.title
        return None

    def get_chapter_id(self, obj):
        if obj.lesson and obj.lesson.chapter:
            return obj.lesson.chapter.id
        if obj.topic and obj.topic.lesson and obj.topic.lesson.chapter:
            return obj.topic.lesson.chapter.id
        return None

    def get_lesson_number(self, obj):
        if obj.lesson:
            return obj.lesson.lesson_number
        return None


    def get_status(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return 'NOT_STARTED'
            
        progress = obj.progress_records.filter(user=user).first()
        return progress.status if progress else 'NOT_STARTED'

    def get_mastery_level(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return None
            
        progress = obj.progress_records.filter(user=user).first()
        return progress.mastery_level if progress else None

    def get_error_tags(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return []
            
        progress = obj.progress_records.filter(user=user).first()
        return progress.error_tags if progress else []

    def get_topics_list(self, obj):
        if obj.item_type == 'LESSON' and obj.lesson:
            return [t.title for t in obj.lesson.topics.all()]
        return []

class LearningPathSerializer(serializers.ModelSerializer):
    items = LearningPathItemSerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True, default='')
    grade_level = serializers.IntegerField(source='subject.grade_level', read_only=True, default=0)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True, default=None)
    total_items = serializers.SerializerMethodField()
    completed_items = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = LearningPath
        fields = [
            'id', 'user', 'subject', 'subject_name', 'grade_level',
            'chapter', 'chapter_title',
            'pre_test_score', 'strategy', 'ai_feedback', 'status', 'created_at', 
            'items', 'total_items', 'completed_items', 'progress_percentage'
        ]

    def get_total_items(self, obj):
        return obj.items.count()

    def get_completed_items(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return 0
        # Đếm số lượng Progress COMPLETED của user này cho các item thuộc lộ trình này
        from apps.users.models import LearningProgress
        return LearningProgress.objects.filter(
            user=user, 
            learning_path_item__learning_path=obj,
            status='COMPLETED'
        ).count()

    def get_progress_percentage(self, obj):
        total = self.get_total_items(obj)
        if total == 0:
            return 0
        completed = self.get_completed_items(obj)
        return round((completed / total) * 100, 1)
