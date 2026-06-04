from rest_framework import serializers
from .models import Quiz, Question, Answer, QuizSubmission


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'answer_text', 'order_num']
        # KHÔNG expose is_correct cho client khi làm bài


class AnswerWithCorrectSerializer(serializers.ModelSerializer):
    """Dùng sau khi submit — trả về đáp án đúng để hiển thị kết quả."""
    class Meta:
        model = Answer
        fields = ['id', 'answer_text', 'is_correct', 'order_num']


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    bloom_display = serializers.SerializerMethodField()
    difficulty_display = serializers.SerializerMethodField()

    def get_bloom_display(self, obj):
        choices = dict(Question.LEVEL_CHOICES)
        return choices.get(obj.bloom_level, f"Mức {obj.bloom_level}")

    def get_difficulty_display(self, obj):
        choices = dict(Question.LEVEL_CHOICES)
        # Nếu difficulty_level sai lệch (do AI nạp nhầm), dùng bloom_level để hiển thị
        display = choices.get(obj.difficulty_level)
        if not display:
            display = choices.get(obj.bloom_level, f"Độ khó {obj.difficulty_level}")
        return display

    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'question_type', 'topic', 
            'difficulty_level', 'bloom_level', 'difficulty_display', 'bloom_display',
            'chapter_title', 'order_num', 'answers'
        ]


class QuestionWithAnswerSerializer(serializers.ModelSerializer):
    """Dùng sau khi submit — bao gồm đáp án đúng và giải thích."""
    answers = AnswerWithCorrectSerializer(many=True, read_only=True)
    bloom_display = serializers.SerializerMethodField()
    difficulty_display = serializers.SerializerMethodField()

    def get_bloom_display(self, obj):
        choices = dict(Question.LEVEL_CHOICES)
        return choices.get(obj.bloom_level, f"Mức {obj.bloom_level}")

    def get_difficulty_display(self, obj):
        choices = dict(Question.LEVEL_CHOICES)
        display = choices.get(obj.difficulty_level)
        if not display:
            display = choices.get(obj.bloom_level, f"Độ khó {obj.difficulty_level}")
        return display

    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'question_type', 'topic',
            'difficulty_level', 'bloom_level', 'difficulty_display', 'bloom_display',
            'chapter_title', 'order_num', 'answers', 'explanation'
        ]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'subject', 'quiz_type', 'title', 'description',
            'difficulty', 'passing_score', 'chapter_coverage',
            'question_count', 'questions'
        ]

    def get_question_count(self, obj):
        return obj.questions.count()


class QuizSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSubmission
        fields = [
            'id', 'user', 'quiz', 'score', 'answers_data', 
            'wrong_chapters', 'bloom_analysis', 'passed', 'submitted_at'
        ]
        read_only_fields = ['user', 'submitted_at', 'score', 'wrong_chapters', 'bloom_analysis', 'passed']


class PreTestSubmitSerializer(serializers.Serializer):
    """Serializer cho API nộp bài pre-test."""
    quiz_id = serializers.IntegerField()
    # {"question_id": answer_id, "3": 12, "4": 15, ...}
    answers = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Map question_id -> answer_id"
    )
