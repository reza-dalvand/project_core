from django.contrib import admin
from apps.core.admin_mixins import AppAdminMixin, AppStaffMixin
from .models import Notification, PushDevice, SMSTemplate, SMSLog


@admin.register(Notification)
class NotificationAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'is_pushed', 'created_at']
    list_filter = ['type', 'is_read', 'is_pushed', 'created_at']
    search_fields = ['user__phone', 'title', 'body']
    readonly_fields = ['created_at', 'read_at']
    raw_id_fields = ['user']
    actions = ['mark_as_read', 'mark_as_unread']

    @admin.action(description='✅ علامت‌گذاری به عنوان خوانده شده')
    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_read=True, read_at=timezone.now())

    @admin.action(description='❌ علامت‌گذاری به عنوان خوانده نشده')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)


@admin.register(PushDevice)
class PushDeviceAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['user', 'platform', 'device_name', 'is_active', 'last_used_at']
    list_filter = ['platform', 'is_active', 'last_used_at']
    search_fields = ['user__phone', 'token', 'device_name']
    readonly_fields = ['last_used_at', 'created_at']
    raw_id_fields = ['user']
    actions = ['deactivate_devices']

    @admin.action(description='🚫 غیرفعال‌سازی دستگاه‌ها')
    def deactivate_devices(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(SMSTemplate)
class SMSTemplateAdmin(AppAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'type', 'provider_template_id', 'is_active', 'updated_at']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'pattern']


@admin.register(SMSLog)
class SMSLogAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['phone', 'template', 'status', 'cost', 'sent_at', 'delivered_at']
    list_filter = ['status', 'sent_at', 'delivered_at']
    search_fields = ['phone', 'message', 'provider_message_id']
    readonly_fields = ['sent_at', 'delivered_at']
    raw_id_fields = ['user', 'template']
    date_hierarchy = 'sent_at'