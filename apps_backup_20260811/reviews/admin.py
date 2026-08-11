from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'business', 'service',
        'rating', 'has_reply', 'created_at',
    ]
    list_filter = ['rating', 'created_at']
    search_fields = ['customer__phone', 'business__name', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['customer', 'appointment', 'business', 'service']

    def has_reply(self, obj):
        return bool(obj.reply)
    has_reply.boolean = True
    has_reply.short_description = 'پاسخ'