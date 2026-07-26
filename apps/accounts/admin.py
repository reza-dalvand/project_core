"""
Admin configuration for accounts app
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.core.admin_mixins import AppAdminMixin, AppStaffMixin
from .models import CustomUser, OTP, ActiveDevice  # ← باید از .models ایمپورت شود


@admin.register(CustomUser)
class CustomUserAdmin(AppAdminMixin, UserAdmin):
    model = CustomUser
    list_display = ['phone', 'full_name', 'role', 'is_verified', 'is_active', 'date_joined']
    list_filter = ['role', 'is_verified', 'is_active', 'is_staff']
    search_fields = ['phone', 'full_name', 'national_id']
    ordering = ['-date_joined']

    fieldsets = (
        ('🔐 اطلاعات احراز هویت', {'fields': ('phone', 'password')}),
        ('👤 اطلاعات پروفایل', {'fields': ('full_name', 'avatar', 'role')}),
        ('🆔 اطلاعات ملی', {'fields': ('national_id', 'national_id_verified', 'verified_name'), 'classes': ('collapse',)}),
        ('⚡ وضعیت حساب', {'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser')}),
        ('⚙️ تنظیمات', {'fields': ('theme', 'notification_enabled'), 'classes': ('collapse',)}),
        ('📅 تاریخ‌ها', {'fields': ('last_login', 'date_joined', 'last_login_ip')}),
        ('🔑 دسترسی‌ها', {'fields': ('groups', 'user_permissions'), 'classes': ('collapse',)}),
    )

    add_fieldsets = (
        ('ساخت کاربر جدید', {
            'classes': ('wide',),
            'fields': ('phone', 'full_name', 'role', 'password1', 'password2', 'is_verified', 'is_active'),
        }),
    )


@admin.register(OTP)
class OTPAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['phone', 'purpose', 'is_used', 'is_expired', 'attempts', 'created_at']
    list_filter = ['purpose', 'is_used', 'created_at']
    search_fields = ['phone']

    def has_add_permission(self, request):
        return False


@admin.register(ActiveDevice)
class ActiveDeviceAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['user', 'device_type', 'device_name', 'is_trusted', 'last_active']
    list_filter = ['device_type', 'is_trusted']
    search_fields = ['user__phone', 'device_name']