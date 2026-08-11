"""
مدل‌های اعلان‌ها و پیامک
- Notification: اعلان‌های داخلی اپ
- PushDevice: دستگاه‌های ثبت‌شده برای ارسال Push
- SMSTemplate: قالب‌های پیامک
- SMSLog: لاگ پیامک‌های ارسال شده
"""
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """اعلان داخلی اپلیکیشن"""

    class Type(models.TextChoices):
        BOOKING_CONFIRMED = 'booking_confirmed', 'تایید رزرو'
        BOOKING_REMINDER = 'booking_reminder', 'یادآوری نوبت'
        BOOKING_CANCELLED = 'booking_cancelled', 'لغو نوبت'
        BOOKING_DONE = 'booking_done', 'انجام خدمت'
        PAYMENT_SUCCESS = 'payment_success', 'پرداخت موفق'
        PAYMENT_REFUNDED = 'payment_refunded', 'استرداد وجه'
        SETTLEMENT_COMPLETED = 'settlement_completed', 'تسویه تکمیل شد'
        NEW_REVIEW = 'new_review', 'نظر جدید'
        BUSINESS_APPROVED = 'business_approved', 'تایید کسب‌وکار'
        BUSINESS_REJECTED = 'business_rejected', 'رد کسب‌وکار'
        SYSTEM = 'system', 'سیستمی'
        PROMO = 'promo', 'تبلیغاتی'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='کاربر',
    )
    type = models.CharField(
        'نوع اعلان',
        max_length=30,
        choices=Type.choices,
    )
    title = models.CharField('عنوان', max_length=200)
    body = models.TextField('متن')
    data = models.JSONField(
        'داده‌های تکمیلی (JSON)',
        default=dict,
        blank=True,
        help_text='مثلاً appointment_id یا deep_link',
    )
    is_read = models.BooleanField('خوانده شده', default=False)
    is_pushed = models.BooleanField('Push ارسال شده', default=False)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    read_at = models.DateTimeField('تاریخ خوانده شدن', null=True, blank=True)

    class Meta:
        verbose_name = '🔔 اعلان'
        verbose_name_plural = '🔔 اعلان‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'type']),
        ]

    def __str__(self):
        return f'{self.user.phone} - {self.title}'

    def mark_as_read(self):
        """علامت‌گذاری به عنوان خوانده شده"""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class PushDevice(models.Model):
    """دستگاه‌های ثبت‌شده برای ارسال Push Notification"""

    class Platform(models.TextChoices):
        ANDROID = 'android', 'اندروید'
        IOS = 'ios', 'آی‌او‌اس'
        WEB = 'web', 'وب'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_devices',
        verbose_name='کاربر',
    )
    platform = models.CharField(
        'پلتفرم',
        max_length=10,
        choices=Platform.choices,
    )
    token = models.CharField(
        'توکن دستگاه (FCM/APNs)',
        max_length=500,
        unique=True,
    )
    device_name = models.CharField('نام دستگاه', max_length=200, blank=True, default='')
    app_version = models.CharField('نسخه اپلیکیشن', max_length=20, blank=True, default='')
    is_active = models.BooleanField('فعال', default=True)
    last_used_at = models.DateTimeField('آخرین استفاده', auto_now=True)
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)

    class Meta:
        verbose_name = '📱 دستگاه Push'
        verbose_name_plural = '📱 دستگاه‌های Push'
        ordering = ['-last_used_at']

    def __str__(self):
        return f'{self.user.phone} - {self.get_platform_display()} - {self.device_name}'


class SMSTemplate(models.Model):
    """قالب‌های پیامک"""

    class Type(models.TextChoices):
        OTP_LOGIN = 'otp_login', 'OTP ورود'
        OTP_CHANGE_PHONE = 'otp_change_phone', 'OTP تغییر شماره'
        BOOKING_CONFIRMED = 'booking_confirmed', 'تایید رزرو'
        BOOKING_REMINDER = 'booking_reminder', 'یادآوری نوبت'
        BOOKING_CANCELLED = 'booking_cancelled', 'لغو نوبت'
        PAYMENT_SUCCESS = 'payment_success', 'پرداخت موفق'
        REFUND_COMPLETED = 'refund_completed', 'استرداد وجه'
        BUSINESS_APPROVED = 'business_approved', 'تایید کسب‌وکار'
        BUSINESS_REJECTED = 'business_rejected', 'رد کسب‌وکار'
        VERIFICATION_CODE = 'verification_code', 'کد تایید نوبت'

    type = models.CharField(
        'نوع قالب',
        max_length=30,
        choices=Type.choices,
        unique=True,
    )
    name = models.CharField('نام قالب', max_length=100)
    provider_template_id = models.CharField(
        'شناسه قالب در سرویس‌دهنده',
        max_length=100,
        help_text='مثلاً template_id کاوه‌نگار',
    )
    pattern = models.TextField(
        'متن قالب (با متغیر)',
        help_text='مثلاً: کد تایید شما: {code}',
    )
    variables = models.JSONField(
        'متغیرها',
        default=list,
        blank=True,
        help_text='لیست متغیرها: ["code", "name"]',
    )
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '📝 قالب پیامک'
        verbose_name_plural = '📝 قالب‌های پیامک'
        ordering = ['type']

    def __str__(self):
        return f'{self.name} ({self.get_type_display()})'


class SMSLog(models.Model):
    """لاگ پیامک‌های ارسال شده"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار ارسال'
        SENT = 'sent', 'ارسال شده'
        DELIVERED = 'delivered', 'تحویل شده'
        FAILED = 'failed', 'ناموفق'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_logs',
        verbose_name='کاربر',
    )
    phone = models.CharField('شماره موبایل', max_length=11, db_index=True)
    template = models.ForeignKey(
        SMSTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name='قالب',
    )
    message = models.TextField('متن پیامک')
    variables = models.JSONField('متغیرهای استفاده شده', default=dict, blank=True)
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    provider_message_id = models.CharField(
        'شناسه پیام در سرویس‌دهنده',
        max_length=100,
        blank=True,
        default='',
    )
    error_message = models.TextField('پیام خطا', blank=True, default='')
    cost = models.PositiveIntegerField('هزینه (ریال)', default=0)
    sent_at = models.DateTimeField('تاریخ ارسال', auto_now_add=True)
    delivered_at = models.DateTimeField('تاریخ تحویل', null=True, blank=True)

    class Meta:
        verbose_name = '📨 لاگ پیامک'
        verbose_name_plural = '📨 لاگ پیامک‌ها'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['phone', '-sent_at']),
            models.Index(fields=['status', '-sent_at']),
        ]

    def __str__(self):
        return f'{self.phone} - {self.get_status_display()} - {self.sent_at}'