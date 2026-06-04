from django.urls import path
from .views import ChatHistoryView, SaveChatPairView, ClearHistoryView, ChatThreadListCreateView, ChatThreadDeleteView

urlpatterns = [
    path('threads/', ChatThreadListCreateView.as_view(), name='chat-thread-list'),
    path('threads/<uuid:pk>/', ChatThreadDeleteView.as_view(), name='chat-thread-delete'),
    path('history/', ChatHistoryView.as_view(), name='chat-history'),
    path('save/', SaveChatPairView.as_view(), name='save-chat-pair'),
    path('clear/', ClearHistoryView.as_view(), name='clear-history'),
]
