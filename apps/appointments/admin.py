from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'business', 'service',
        'date_key', 'time_slot', 'status',
        'total_price', 'deposit_amount', 'has_review',
    ]
    list_filter = ['status', 'has_review', 'is_trust_based']
    search_fields = ['customer__phone', 'business__name', 'service__name']
    readonly_fields = ['verification_code', 'date_key', 'remaining_amount']
    date_hierarchy = 'created_at'
    fieldsets = (
        ('📅 اطلاعات نوبت', {
            'fields': ('business', 'service', 'customer', 'jy', 'jm', 'jd', 'date_key', 'time_slot', 'status'),
        }),
        # ❌ team_member حذف شد
        ('✅ تایید', {
            'fields': ('verification_code', 'is_trust_based', 'is_verified', 'verified_at'),
        }),
        ('❌ لغو', {
            'fields': ('cancellation_reason', 'cancelled_at'),
        }),
        ('💰 مالی', {
            'fields': ('total_price', 'deposit_amount', 'remaining_amount'),
        }),
        ('🔔 یادآوری', {
            'fields': ('reminder_sent', 'reminder_sent_at'),
        }),
        ('⭐ نظردهی', {
            'fields': ('has_review',),
        }),
    )