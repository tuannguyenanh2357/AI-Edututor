from django.contrib import admin
from .models import Subject, SubjectDocument

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')

@admin.register(SubjectDocument)
class SubjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subject', 'uploaded_at')
    list_filter = ('subject',)
    search_fields = ('title', 'content')
