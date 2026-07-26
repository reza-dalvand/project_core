"""
مدل کاربر سفارشی با نقش‌ها
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    مدل کاربر سفارشی

    احراز هویت با شماره موبایل انجام می‌شود.
    نقش‌ها:
    - customer: کاربر عادی (مشتری)
    - business_owner: صاحب کسب‌وکار
    - app_staff: کارمند اپ (پشتیبان)
    - app_admin: ادمین بک‌اند اپ
    - landing_admin: ادمین سایت معرفی
    - super_admin: مدیر ارشد (دسترسی کامل)
    """

    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'مشتری'
        BUSINESS_OWNER = 'business_owner', 'صاحب کسب‌وکار'
        APP_STAFF = 'app_staff', 'کارمند اپ (پشتیبان)'
        APP_ADMIN = 'app_admin', 'ادمین بک‌اند اپ'
        LANDING_ADMIN = 'landing_admin', 'ادمین سایت معرفی'
        SUPER_ADMIN = 'super_admin', 'مدیر ارشد'

    # ═══════════════════════════════════════════
    #   فیلدهای اصلی احراز هویت
    # ═══════════════════════════════════════════
    phone = models.CharField(
        'شماره موبایل',
        max_length=11,
        unique=True,
        db_index=True,
        help_text='شماره موبایل ۱۱ رقمی (مثال: 09123456789)'
    )

    role = models.CharField(
        'نقش',
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )

    # ═══════════════════════════════════════════
    #   اطلاعات پروفایل
    # ═══════════════════════════════════════════
    full_name = models.CharField(
        'نام و نام خانوادگی',
        max_length=150,
        blank=True,
        default='',
    )

    avatar = models.ImageField(
        'عکس پروفایل',
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
    )

    # ═══════════════════════════════════════════
    #   اطلاعات ملی (برای احراز هویت صاحب کسب‌وکار)
    # ═══════════════════════════════════════════
    national_id = models.CharField(
        'کد ملی',
        max_length=10,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
    )

    national_id_verified = models.BooleanField(
        'کد ملی تایید شده',
        default=False,
    )

    verified_name = models.CharField(
        'نام تایید شده (از استعلام)',
        max_length=150,
        blank=True,
        default='',
    )

    # ═══════════════════════════════════════════
    #   وضعیت حساب
    # ═══════════════════════════════════════════
    is_verified = models.BooleanField(
        'حساب تایید شده',
        default=False,
        help_text='آیا شماره موبایل با OTP تایید شده؟'
    )

    is_active = models.BooleanField(
        'فعال',
        default=True,
    )

    is_staff = models.BooleanField(
        'دسترسی به پنل ادمین',
        default=False,
    )

    # ═══════════════════════════════════════════
    #   تاریخ‌ها
    # ═══════════════════════════════════════════
    date_joined = models.DateTimeField(
        'تاریخ عضویت',
        default=timezone.now,
    )

    last_login_ip = models.GenericIPAddressField(
        'آخرین IP ورود',
        blank=True,
        null=True,
    )

    # ═══════════════════════════════════════════
    #   تنظیمات کاربر
    # ═══════════════════════════════════════════
    theme = models.CharField(
        'تم اپلیکیشن',
        max_length=10,
        choices=[
            ('light', 'روشن'),
            ('dark', 'تاریک'),
            ('system', 'خودکار'),
        ],
        default='system',
    )

    notification_enabled = models.BooleanField(
        'اعلان‌ها فعال',
        default=True,
    )

    # ═══════════════════════════════════════════
    #   Manager
    # ═══════════════════════════════════════════
    objects = CustomUserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []  # برای createsuperuser

    class Meta:
        verbose_name = '👤 کاربر'
        verbose_name_plural = '👤 کاربران'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['role']),
            models.Index(fields=['national_id']),
        ]

    def __str__(self):
        name = self.full_name or self.phone
        return f'{name} ({self.get_role_display()})'

    # ═══════════════════════════════════════════
    #   متدهای کمکی نقش
    # ═══════════════════════════════════════════
    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_business_owner(self):
        return self.role == self.Role.BUSINESS_OWNER

    @property
    def is_app_staff(self):
        return self.role in [
            self.Role.APP_STAFF,
            self.Role.APP_ADMIN,
            self.Role.SUPER_ADMIN,
        ]

    @property
    def is_app_admin(self):
        return self.role in [
            self.Role.APP_ADMIN,
            self.Role.SUPER_ADMIN,
        ]

    @property
    def is_landing_admin(self):
        return self.role in [
            self.Role.LANDING_ADMIN,
            self.Role.SUPER_ADMIN,
        ]

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def can_access_app_admin(self):
        """دسترسی به پنل ادمین بک‌اند اپ"""
        return self.role in [
            self.Role.SUPER_ADMIN,
            self.Role.APP_ADMIN,
            self.Role.APP_STAFF,
        ]

    @property
    def can_access_landing_admin(self):
        """دسترسی به پنل ادمین سایت معرفی"""
        return self.role in [
            self.Role.SUPER_ADMIN,
            self.Role.LANDING_ADMIN,
        ]

    @property
    def display_name(self):
        """نام نمایشی کاربر"""
        if self.full_name:
            return self.full_name
        if self.verified_name:
            return self.verified_name
        return self.phone

    def get_short_name(self):
        return self.full_name or self.phone

    def get_full_name(self):
        return self.full_name or self.phone


class OTP(models.Model):
    """
    کدهای تایید یکبار مصرف (OTP)
    برای ورود، تغییر شماره و...
    """

    class Purpose(models.TextChoices):
        LOGIN = 'login', 'ورود'
        CHANGE_PHONE = 'change_phone', 'تغییر شماره'
        VERIFY_NATIONAL_ID = 'verify_national_id', 'تایید کد ملی'
        RESET_PASSWORD = 'reset_password', 'بازیابی رمز عبور'

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='otps',
        verbose_name='کاربر',
        null=True,
        blank=True,
    )

    phone = models.CharField(
        'شماره موبایل',
        max_length=11,
        db_index=True,
    )

    code = models.CharField(
        'کد تایید',
        max_length=6,
    )

    purpose = models.CharField(
        'هدف',
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.LOGIN,
    )

    is_used = models.BooleanField(
        'استفاده شده',
        default=False,
    )

    attempts = models.PositiveSmallIntegerField(
        'تعداد تلاش',
        default=0,
    )

    max_attempts = models.PositiveSmallIntegerField(
        'حداکثر تلاش',
        default=5,
    )

    expires_at = models.DateTimeField(
        'تاریخ انقضا',
    )

    created_at = models.DateTimeField(
        'تاریخ ایجاد',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = '🔑 کد تایید'
        verbose_name_plural = '🔑 کدهای تایید'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'purpose', '-created_at']),
        ]

    def __str__(self):
        return f'OTP for {self.phone} ({self.purpose})'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired and self.attempts < self.max_attempts

    def verify(self, entered_code):
        """بررسی صحت کد"""
        self.attempts += 1

        if self.code == entered_code and self.is_valid:
            self.is_used = True
            self.save(update_fields=['is_used', 'attempts'])
            return True

        self.save(update_fields=['attempts'])
        return False


class ActiveDevice(models.Model):
    """
    دستگاه‌های فعال کاربر (Session Management)
    """

    class DeviceType(models.TextChoices):
        ANDROID = 'android', 'اندروید'
        IOS = 'ios', 'آیفون'
        WEB = 'web', 'وب'

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='devices',
        verbose_name='کاربر',
    )

    device_type = models.CharField(
        'نوع دستگاه',
        max_length=10,
        choices=DeviceType.choices,
        default=DeviceType.ANDROID,
    )

    device_name = models.CharField(
        'نام دستگاه',
        max_length=200,
        blank=True,
        default='',
    )

    os_version = models.CharField(
        'نسخه سیستم‌عامل',
        max_length=50,
        blank=True,
        default='',
    )

    app_version = models.CharField(
        'نسخه اپلیکیشن',
        max_length=20,
        blank=True,
        default='',
    )

    ip_address = models.GenericIPAddressField(
        'آی‌پی',
        blank=True,
        null=True,
    )

    location = models.CharField(
        'موقعیت',
        max_length=200,
        blank=True,
        default='',
    )

    is_trusted = models.BooleanField(
        'مورد اعتماد',
        default=True,
    )

    last_active = models.DateTimeField(
        'آخرین فعالیت',
        auto_now=True,
    )

    created_at = models.DateTimeField(
        'تاریخ ایجاد',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = '📱 دستگاه فعال'
        verbose_name_plural = '📱 دستگاه‌های فعال'
        ordering = ['-last_active']

    def __str__(self):
        return f'{self.device_name} - {self.user.phone}'