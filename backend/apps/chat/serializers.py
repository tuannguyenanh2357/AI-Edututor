from rest_framework import serializers
from .models import Message, ChatThread

class ChatThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatThread
        fields = ['id', 'user', 'subject', 'title', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

class MessageSerializer(serializers.ModelSerializer):
    image_data = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'thread', 'user', 'role', 'content', 'source_metadata', 'created_at', 'image_data']
        read_only_fields = ['user', 'created_at']

    def get_image_data(self, obj):
        upload = obj.uploads.first()
        return upload.image_data if upload else None
