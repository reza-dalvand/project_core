from django.contrib import admin
from .models import FAQ, SupportTicket


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'category', 'sort_order', 'is_active']
    list_editable = ['sort_order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['question']

    def question_preview(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_preview.short_description = 'سوال'


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'subject', 'status', 'priority',
        'created_at', 'responded_at',
    ]
    list_filter = ['status', 'priority']
    search_fields = ['user__phone', 'subject', 'message']
    readonly_fields = ['created_at', 'responded_at']