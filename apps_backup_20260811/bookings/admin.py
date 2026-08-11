
from django.contrib import admin
from apps.core.admin_mixins import AppStaffMixin
from .models import Schedule, ScheduleBreak, TimeSlot, Appointment, CancellationRequest


class ScheduleBreakInline(admin.TabularInline):
    model = ScheduleBreak
    extra = 1


@admin.register(Schedule)
class ScheduleAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['business', 'weekday', 'is_working', 'start_time', 'end_time', 'slot_duration']
    list_filter = ['weekday', 'is_working']
    search_fields = ['business__name']
    inlines = [ScheduleBreakInline]


@admin.register(TimeSlot)
class TimeSlotAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['business', 'service', 'date', 'start_time', 'end_time', 'status']
    list_filter = ['status', 'date']
    search_fields = ['business__name', 'service__name']


@admin.register(Appointment)
class AppointmentAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = [
        'id', 'customer', 'business', 'service',
        'date', 'time', 'status', 'final_price', 'deposit_paid'
    ]
    list_filter = ['status', 'date', 'deposit_paid']
    search_fields = ['customer__phone', 'customer__full_name', 'business__name']
    readonly_fields = ['verification_code', 'code_generated_at', 'created_at']
    date_hierarchy = 'date'


@admin.register(CancellationRequest)
class CancellationRequestAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['appointment', 'requested_by', 'reason_type', 'status', 'refund_amount', 'created_at']
    list_filter = ['status', 'reason_type']
    search_fields = ['appointment__customer__phone']