from django.contrib import admin
from .models import Battle, BattleResult


class BattleResultInline(admin.TabularInline):
    model  = BattleResult
    extra  = 0
    readonly_fields = ['player', 'score', 'correct_count', 'total_time', 'submitted_at']
    can_delete = False


@admin.register(Battle)
class BattleAdmin(admin.ModelAdmin):
    list_display  = ['id', 'challenger', 'opponent', 'grade_level', 'status', 'winner', 'created_at']
    list_filter   = ['status', 'grade_level']
    search_fields = ['challenger__username', 'opponent__username']
    readonly_fields = ['created_at', 'expires_at', 'question_ids']
    inlines = [BattleResultInline]

    actions = ['force_expire']

    @admin.action(description='Đánh dấu các trận đấu đã chọn là HẾT HẠN')
    def force_expire(self, request, queryset):
        updated = queryset.filter(
            status__in=[Battle.STATUS_PENDING, Battle.STATUS_IN_PROGRESS]
        ).update(status=Battle.STATUS_EXPIRED)
        self.message_user(request, f'Đã hủy {updated} trận đấu.')


@admin.register(BattleResult)
class BattleResultAdmin(admin.ModelAdmin):
    list_display  = ['battle', 'player', 'score', 'correct_count', 'total_time', 'submitted_at']
    list_filter   = ['battle__status']
    search_fields = ['player__username']
