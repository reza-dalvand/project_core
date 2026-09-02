"""
Admin configuration for accounts app
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OtpCode, UserDevice, UserReferral, UserBankInfo


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = [
        'phone', 'first_name', 'last_name',
        'is_verified', 'is_active', 'date_joined',
    ]
    list_filter = ['is_verified', 'is_active', 'is_staff']
    search_fields = ['phone', 'first_name', 'last_name', 'national_id']
    ordering = ['-date_joined']
    fieldsets = (
        ('🔐 اطلاعات احراز هویت', {'fields': ('phone', 'password')}),
        ('👤 اطلاعات پروفایل', {'fields': ('first_name', 'last_name', 'avatar')}),
        ('🆔 اطلاعات ملی', {
            'fields': ('national_id', 'is_national_id_verified', 'verified_name'),
            'classes': ('collapse',),
        }),
        ('⚡ وضعیت حساب', {
            'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser'),
        }),
        ('📅 تاریخ‌ها', {'fields': ('last_login', 'date_joined')}),
        ('🔑 دسترسی‌ها', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
    )
    add_fieldsets = (
        ('ساخت کاربر جدید', {
            'classes': ('wide',),
            'fields': (
                'phone', 'first_name', 'last_name',
                'password1', 'password2',
                'is_verified', 'is_active',
            ),
        }),
    )


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    list_display = ['phone', 'purpose', 'is_used', 'is_expired', 'created_at']
    list_filter = ['purpose', 'is_used', 'created_at']
    search_fields = ['phone']

    def has_add_permission(self, request):
        return False


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'device_name', 'is_current', 'last_active']
    list_filter = ['device_type', 'is_current']
    search_fields = ['user__phone', 'device_name']


@admin.register(UserReferral)
class UserReferralAdmin(admin.ModelAdmin):
    list_display = ['user', 'referral_code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['user__phone', 'referral_code']


# ✅ NEW: ثبت مدل UserBankInfo
@admin.register(UserBankInfo)
class UserBankInfoAdmin(admin.ModelAdmin):
    list_display = ['user', 'bank_name', 'owner_name', 'is_complete', 'updated_at']
    list_filter = ['is_complete', 'bank_name']
    search_fields = ['user__phone', 'owner_name', 'sheba', 'card_number']
    readonly_fields = ['is_complete', 'created_at', 'updated_at']
    raw_id_fields = ['user']
    fieldsets = (
        ('🏦 اطلاعات بانکی', {
            'fields': ('user', 'bank_name', 'bank_id', 'sheba', 'card_number', 'owner_name'),
        }),
        ('📊 وضعیت', {
            'fields': ('is_complete', 'created_at', 'updated_at'),
        }),
    )