"""
تنظیمات پنل ادمین برای مدل‌های احراز هویت
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, OTP, ActiveDevice


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """پنل ادمین سفارشی برای کاربران"""

    model = CustomUser

    list_display = [
        'phone', 'full_name', 'role',
        'is_verified', 'is_active', 'date_joined'
    ]

    list_filter = [
        'role', 'is_verified', 'is_active',
        'is_staff', 'national_id_verified'
    ]

    search_fields = ['phone', 'full_name', 'national_id']

    ordering = ['-date_joined']

    fieldsets = (
        ('🔐 اطلاعات احراز هویت', {
            'fields': ('phone', 'password'),
        }),
        ('👤 اطلاعات پروفایل', {
            'fields': ('full_name', 'avatar', 'role'),
        }),
        ('🆔 اطلاعات ملی', {
            'fields': ('national_id', 'national_id_verified', 'verified_name'),
            'classes': ('collapse',),
        }),
        ('⚡ وضعیت حساب', {
            'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser'),
        }),
        ('⚙️ تنظیمات', {
            'fields': ('theme', 'notification_enabled'),
            'classes': ('collapse',),
        }),
        ('📅 تاریخ‌ها', {
            'fields': ('last_login', 'date_joined', 'last_login_ip'),
        }),
        ('🔑 دسترسی‌ها', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        ('ساخت کاربر جدید', {
            'classes': ('wide',),
            'fields': (
                'phone', 'full_name', 'role',
                'password1', 'password2',
                'is_verified', 'is_active',
            ),
        }),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """پنل ادمین کدهای تایید"""

    list_display = [
        'phone', 'purpose', 'is_used',
        'is_expired', 'attempts', 'created_at'
    ]

    list_filter = ['purpose', 'is_used', 'created_at']
    search_fields = ['phone']
    readonly_fields = ['created_at']


@admin.register(ActiveDevice)
class ActiveDeviceAdmin(admin.ModelAdmin):
    """پنل ادمین دستگاه‌های فعال"""

    list_display = [
        'user', 'device_type', 'device_name',
        'is_trusted', 'last_active'
    ]

    list_filter = ['device_type', 'is_trusted']
    search_fields = ['user__phone', 'device_name']