from django.urls import path
from .views import SubjectListView, SubjectDetailView

urlpatterns = [
    path('', SubjectListView.as_view(), name='subject-list'),
    path('<int:id>/', SubjectDetailView.as_view(), name='subject-detail'),
]
