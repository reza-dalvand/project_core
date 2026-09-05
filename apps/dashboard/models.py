"""
مدل‌های داشبورد مدیریت — نقش‌ها و ادمین‌ها
"""
from django.db import models
from django.conf import settings


class AdminRole(models.Model):
    """نقش‌های ادمین"""
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'سوپر ادمین'
        APP_ADMIN = 'app_admin', 'ادمین اپلیکیشن'
        CONTENT_ADMIN = 'content_admin', 'ادمین محتوا'
        FINANCIAL_ADMIN = 'financial_admin', 'ادمین مالی'
        SUPPORT_ADMIN = 'support_admin', 'پشتیبانی'

    name = models.CharField(
        'نام نقش',
        max_length=50,
        choices=Role.choices,
        unique=True,
    )
    description = models.TextField(
        'توضیحات',
        blank=True,
        default='',
    )
    permissions = models.JSONField(
        'دسترسی‌ها',
        default=list,
        blank=True,
        help_text='لیست دسترسی‌ها',
    )
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_roles'
        verbose_name = '🎭 نقش ادمین'
        verbose_name_plural = '🎭 نقش‌های ادمین'
        ordering = ['name']

    def __str__(self):
        return self.get_name_display()


class AdminUser(models.Model):
    """کاربران ادمین"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        verbose_name='کاربر',
    )
    role = models.ForeignKey(
        AdminRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admins',
        verbose_name='نقش',
    )
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'admin_users'
        verbose_name = '👨‍💼 ادمین'
        verbose_name_plural = '👨‍💼 ادمین‌ها'
        ordering = ['-created_at']

    def __str__(self):
        role_name = self.role.name if self.role else "بدون نقش"
        return f'{self.user.phone} - {role_name}'


# apps/dashboard/models.py — اضافه شود در انتهای فایل

class AuditLog(models.Model):
    """
    لاگ حسابرسی داشبورد ادمین
    ✅ فاز ۱: جایگزین لیست حافظه‌ای _audit_logs
    تمام عملیات‌های حساس پنل ادمین اینجا ثبت می‌شوند
    """

    class Severity(models.TextChoices):
        INFO = 'info', 'اطلاعاتی'
        WARNING = 'warning', 'هشدار'
        CRITICAL = 'critical', 'بحرانی'

    action = models.CharField(
        'عملیات',
        max_length=100,
        db_index=True,
        help_text='مثلاً: business.approved',
    )
    admin_phone = models.CharField(
        'شماره ادمین',
        max_length=20,
    )
    admin_role = models.CharField(
        'نقش ادمین',
        max_length=50,
    )
    client_ip = models.CharField(
        'آدرس IP',
        max_length=45,
        blank=True,
        default='',
    )
    target_type = models.CharField(
        'نوع هدف',
        max_length=50,
        blank=True,
        default='',
    )
    target_id = models.CharField(
        'شناسه هدف',
        max_length=50,
        blank=True,
        null=True,
    )
    target_name = models.CharField(
        'نام هدف',
        max_length=200,
        blank=True,
        default='',
    )
    details = models.JSONField(
        'جزئیات',
        default=dict,
        blank=True,
    )
    severity = models.CharField(
        'شدت',
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFO,
    )
    created_at = models.DateTimeField(
        'زمان ثبت',
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = 'dashboard_audit_logs'
        verbose_name = '📋 لاگ حسابرسی'
        verbose_name_plural = '📋 لاگ‌های حسابرسی'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['admin_phone', '-created_at']),
        ]

    def __str__(self):
        return (
            f'[{self.severity}] {self.action} '
            f'by {self.admin_phone}'
        )