from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'business', 'service',
        'rating', 'has_reply_display', 'created_at',
    ]
    list_filter = ['rating', 'created_at']
    search_fields = ['customer__phone', 'business__name', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['customer', 'appointment', 'business', 'service']

    # ✅ FIX: استفاده از format_html به جای boolean (deprecated)
    @admin.display(description='پاسخ', boolean=True)
    def has_reply_display(self, obj):
        return bool(obj.reply)