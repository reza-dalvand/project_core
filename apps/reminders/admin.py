from django.contrib import admin
from .models import RenewalReminder


@admin.register(RenewalReminder)
class RenewalReminderAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'business', 'service',
        'last_service_date', 'due_date', 'days_remaining',
        'reminder_sent', 'has_new_booking_after_send',
    ]
    list_filter = ['reminder_sent', 'has_new_booking_after_send']
    search_fields = ['customer__phone', 'business__name', 'service__name']