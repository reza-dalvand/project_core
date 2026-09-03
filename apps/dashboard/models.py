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