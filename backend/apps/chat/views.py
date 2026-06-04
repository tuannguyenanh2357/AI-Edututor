from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from .models import Message, ChatThread
from .serializers import MessageSerializer, ChatThreadSerializer
from apps.subjects.models import Subject

class ChatThreadListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return threads for the current user
        return ChatThread.objects.filter(user=self.request.user).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ChatThreadDeleteView(generics.DestroyAPIView):
    serializer_class = ChatThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatThread.objects.filter(user=self.request.user)

class ChatHistoryView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        thread_id = self.request.query_params.get('thread_id')
        if thread_id:
            return Message.objects.filter(user=user, thread_id=thread_id).order_by('created_at')
        return Message.objects.none()

class SaveChatPairView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        thread_id = request.data.get('thread_id')
        subject_id = request.data.get('subject') # used when creating thread
        user_message = request.data.get('user_message', '').strip()
        ai_response = request.data.get('ai_response', '').strip()
        source_metadata = request.data.get('source_metadata', [])
        image_data = request.data.get('image_data')

        if not user_message or not ai_response:
            return Response(
                {"error": "user_message và ai_response không được để trống."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get or create thread
        if not thread_id:
            # create new thread
            subject_obj = Subject.objects.filter(pk=subject_id).first() if subject_id else None
            # Title is first 50 chars of user_message
            title = user_message[:50] + ("..." if len(user_message) > 50 else "")
            thread = ChatThread.objects.create(user=request.user, subject=subject_obj, title=title)
        else:
            thread = get_object_or_404(ChatThread, pk=thread_id, user=request.user)
            # Update the updated_at timestamp
            thread.save()

        # Check global history preference
        if hasattr(request.user, 'is_global_history_enabled') and not request.user.is_global_history_enabled:
             # Just return without saving to DB if history is disabled
             return Response({"status": "saved_temporarily", "thread_id": thread.id}, status=status.HTTP_201_CREATED)

        try:
            user_message_obj = Message.objects.create(
                thread=thread,
                user=request.user,
                role='user',
                content=user_message
            )
            
            if image_data:
                from .models import Upload
                Upload.objects.create(
                    user=request.user,
                    message=user_message_obj,
                    image_data=image_data
                )
                
            Message.objects.create(
                thread=thread,
                user=request.user,
                role='assistant',
                content=ai_response,
                source_metadata=source_metadata
            )
        except Exception as e:
            return Response({"error": f"Lỗi lưu dữ liệu: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "saved", "thread_id": thread.id}, status=status.HTTP_201_CREATED)

class ClearHistoryView(APIView):
    """
    Legacy support or clear a specific thread if passed in body.
    POST /api/chat/clear/
    Body: { "thread_id": "abc..." }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        thread_id = request.data.get('thread_id')
        if not thread_id:
            return Response(
                {"error": "thread_id là bắt buộc."},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count, _ = ChatThread.objects.filter(
            id=thread_id,
            user=request.user
        ).delete()

        return Response({
            "status": "cleared",
            "deleted_count": deleted_count
        }, status=status.HTTP_200_OK)
