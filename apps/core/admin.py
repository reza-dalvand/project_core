from django.contrib import admin

from .models import AppConfig


@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
    list_display = [
        'latest_version',
        'min_required_version',
        'is_force_update',
        'is_maintenance',
    ]

    fieldsets = (
        ('📦 نسخه اپلیکیشن', {
            'fields': (
                'latest_version',
                'min_required_version',
                'is_force_update',
                'update_title',
                'update_message',
                'changelog',
                'store_url',
                'store_name',
            ),
        }),
        ('🔧 حالت تعمیرات', {
            'fields': (
                'is_maintenance',
                'maintenance_title',
                'maintenance_message',
                'maintenance_estimated_end',
                'maintenance_reason',
                'support_phone',
            ),
        }),
    )

    def has_add_permission(self, request):
        """فقط یک رکورد مجاز است"""
        if AppConfig.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """حذف مجاز نیست — فقط ویرایش"""
        return False