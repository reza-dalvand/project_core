from django.contrib import admin
from .models import ServiceSchedule


@admin.register(ServiceSchedule)
class ServiceScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'business', 'service',
        'date_key', 'work_start', 'work_end',
        'slot_duration', 'slot_count',
    ]
    list_filter = ['business', 'service']
    search_fields = ['business__name', 'service__name']
    readonly_fields = ['date_key', 'slot_count']