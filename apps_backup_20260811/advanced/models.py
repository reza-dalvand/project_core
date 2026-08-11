"""
مدل‌های ویژگی‌های پیشرفته:
- SearchHistory: تاریخچه جستجو
- Favorite: علاقه‌مندی‌ها (Generic)
- ReferralCode: کد دعوت
- Referral: ثبت دعوت‌ها
- Report: گزارشات تولید شده
"""
import secrets
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class SearchHistory(models.Model):
    """تاریخچه جستجوهای کاربر"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='search_history',
        verbose_name='کاربر',
    )
    query = models.CharField(
        'عبارت جستجو',
        max_length=200,
        db_index=True,
    )
    result_count = models.PositiveIntegerField(
        'تعداد نتایج',
        default=0,
    )
    category = models.CharField(
        'دسته‌بندی جستجو',
        max_length=50,
        blank=True,
        default='',
        help_text='مثلاً: businesses, services, posts',
    )
    created_at = models.DateTimeField(
        'تاریخ جستجو',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = '🔍 تاریخچه جستجو'
        verbose_name_plural = '🔍 تاریخچه جستجوها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['query']),
        ]

    def __str__(self):
        return f'{self.user.phone} - "{self.query}"'


class Favorite(models.Model):
    """علاقه‌مندی‌ها - Generic برای هر نوع آبجکت"""

    class Type(models.TextChoices):
        BUSINESS = 'business', 'کسب‌وکار'
        POST = 'post', 'پست ویترین'
        SERVICE = 'service', 'خدمت'
        MODEL_REQUEST = 'model_request', 'درخواست مدل'
        LINE_RENTAL = 'line_rental', 'اجاره لاین'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='کاربر',
    )
    favorite_type = models.CharField(
        'نوع علاقه‌مندی',
        max_length=30,
        choices=Type.choices,
    )

    # Generic Foreign Key
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # اطلاعات کمکی (برای سرعت بیشتر)
    business_id = models.PositiveIntegerField(
        'شناسه کسب‌وکار',
        null=True,
        blank=True,
        db_index=True,
    )
    title = models.CharField(
        'عنوان',
        max_length=200,
        blank=True,
        default='',
    )

    created_at = models.DateTimeField(
        'تاریخ افزودن',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = '❤️ علاقه‌مندی'
        verbose_name_plural = '❤️ علاقه‌مندی‌ها'
        ordering = ['-created_at']
        unique_together = [
            ('user', 'favorite_type', 'object_id'),
        ]
        indexes = [
            models.Index(fields=['user', 'favorite_type', '-created_at']),
            models.Index(fields=['favorite_type', 'object_id']),
        ]

    def __str__(self):
        return f'{self.user.phone} ❤️ {self.get_favorite_type_display()}'


class ReferralCode(models.Model):
    """کد معرف کاربر"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_code',
        verbose_name='کاربر',
    )
    code = models.CharField(
        'کد معرف',
        max_length=20,
        unique=True,
        db_index=True,
    )
    is_active = models.BooleanField(
        'فعال',
        default=True,
    )
    total_referrals = models.PositiveIntegerField(
        'تعداد دعوت‌های موفق',
        default=0,
    )
    total_rewards = models.PositiveBigIntegerField(
        'مجموع پاداش‌ها (تومان)',
        default=0,
    )
    created_at = models.DateTimeField(
        'تاریخ ایجاد',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = '🎫 کد معرف'
        verbose_name_plural = '🎫 کدهای معرف'

    def __str__(self):
        return f'{self.user.phone} - {self.code}'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self):
        """تولید کد معرف یکتا"""
        while True:
            # فرمت: ZIBANO-XXXX (4 رقم از انتهای شماره موبایل + 4 رقم تصادفی)
            phone_suffix = self.user.phone[-4:] if self.user.phone else '0000'
            random_part = secrets.token_hex(2).upper()
            code = f'ZIBANO-{phone_suffix}{random_part}'
            if not ReferralCode.objects.filter(code=code).exists():
                return code


class Referral(models.Model):
    """ثبت دعوت‌های موفق"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        COMPLETED = 'completed', 'تکمیل شده'
        REWARDED = 'rewarded', 'پاداش داده شده'
        CANCELLED = 'cancelled', 'لغو شده'

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referrals_made',
        verbose_name='دعوت‌کننده',
    )
    referred = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referred_by',
        verbose_name='دعوت‌شده',
    )
    referral_code = models.ForeignKey(
        ReferralCode,
        on_delete=models.CASCADE,
        related_name='referrals',
        verbose_name='کد معرف',
    )
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # پاداش‌ها
    referrer_reward = models.PositiveBigIntegerField(
        'پاداش دعوت‌کننده (تومان)',
        default=0,
    )
    referred_reward = models.PositiveBigIntegerField(
        'پاداش دعوت‌شده (تومان)',
        default=0,
    )

    # شرط تکمیل: اولین رزرو موفق
    first_booking = models.ForeignKey(
        'bookings.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referral',
        verbose_name='اولین رزرو',
    )

    created_at = models.DateTimeField(
        'تاریخ دعوت',
        auto_now_add=True,
    )
    completed_at = models.DateTimeField(
        'تاریخ تکمیل',
        null=True,
        blank=True,
    )
    rewarded_at = models.DateTimeField(
        'تاریخ پرداخت پاداش',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = '🤝 دعوت'
        verbose_name_plural = '🤝 دعوت‌ها'
        ordering = ['-created_at']
        unique_together = [
            ('referrer', 'referred'),
        ]
        indexes = [
            models.Index(fields=['referrer', 'status']),
            models.Index(fields=['referred']),
        ]

    def __str__(self):
        return f'{self.referrer.phone} → {self.referred.phone}'


class Report(models.Model):
    """گزارشات تولید شده"""

    class Type(models.TextChoices):
        TRANSACTIONS = 'transactions', 'تراکنش‌ها'
        APPOINTMENTS = 'appointments', 'نوبت‌ها'
        REVIEWS = 'reviews', 'نظرات'
        REVENUE = 'revenue', 'درآمد'
        CUSTOMERS = 'customers', 'مشتریان'

    class Format(models.TextChoices):
        EXCEL = 'xlsx', 'Excel'
        CSV = 'csv', 'CSV'
        PDF = 'pdf', 'PDF'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='کاربر',
    )
    report_type = models.CharField(
        'نوع گزارش',
        max_length=30,
        choices=Type.choices,
    )
    format = models.CharField(
        'فرمت',
        max_length=10,
        choices=Format.choices,
        default=Format.EXCEL,
    )
    file = models.FileField(
        'فایل گزارش',
        upload_to='reports/%Y/%m/',
        blank=True,
    )
    filters = models.JSONField(
        'فیلترهای اعمال شده',
        default=dict,
        blank=True,
    )
    records_count = models.PositiveIntegerField(
        'تعداد رکوردها',
        default=0,
    )
    file_size = models.PositiveBigIntegerField(
        'حجم فایل (بایت)',
        default=0,
    )
    is_ready = models.BooleanField(
        'آماده',
        default=False,
    )
    error_message = models.TextField(
        'پیام خطا',
        blank=True,
        default='',
    )
    created_at = models.DateTimeField(
        'تاریخ درخواست',
        auto_now_add=True,
    )
    completed_at = models.DateTimeField(
        'تاریخ تکمیل',
        null=True,
        blank=True,
    )
    expires_at = models.DateTimeField(
        'تاریخ انقضا',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = '📊 گزارش'
        verbose_name_plural = '📊 گزارشات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'report_type', '-created_at']),
        ]

    def __str__(self):
        return f'{self.get_report_type_display()} - {self.user.phone}'