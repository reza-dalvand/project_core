"""
مدل کاربر بیو کلاب — احراز هویت با شماره موبایل
بدون نقش (role) — هر کاربر می‌تواند یک کسب‌وکار داشته باشد
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone

from .managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    """کاربر بیو کلاب — احراز هویت با شماره موبایل"""

    # ═══════════ احراز هویت ═══════════
    phone = models.CharField(
        'شماره موبایل',
        max_length=11,
        unique=True,
        db_index=True,
        help_text='شماره موبایل ۱۱ رقمی (مثال: 09123456789)',
    )

    # ═══════════ پروفایل ═══════════
    first_name = models.CharField(
        'نام',
        max_length=50,
        blank=True,
        default='',
    )
    last_name = models.CharField(
        'نام خانوادگی',
        max_length=50,
        blank=True,
        default='',
    )
    avatar = models.ImageField(
        'عکس پروفایل',
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
    )

    # ═══════════ احراز هویت ملی ═══════════
    national_id = models.CharField(
        'کد ملی',
        max_length=10,
        blank=True,
        default='',
    )
    is_national_id_verified = models.BooleanField(
        'کد ملی تایید شده',
        default=False,
    )
    verified_name = models.CharField(
        'نام تایید شده (از استعلام)',
        max_length=100,
        blank=True,
        default='',
    )

    # ═══════════ وضعیت حساب ═══════════
    is_verified = models.BooleanField(
        'حساب تایید شده',
        default=False,
        help_text='آیا شماره موبایل با OTP تایید شده؟',
    )
    is_staff = models.BooleanField(
        'دسترسی به پنل ادمین',
        default=False,
    )
    is_superuser = models.BooleanField(
        'مدیر ارشد',
        default=False,
    )

    is_active = models.BooleanField(
    'فعال',
    default=True,
    )

    # ═══════════ تاریخ‌ها ═══════════
    date_joined = models.DateTimeField(
        'تاریخ عضویت',
        default=timezone.now,
    )
    last_login = models.DateTimeField(
        'آخرین ورود',
        null=True,
        blank=True,
    )

    # ═══════════ Manager ═══════════
    objects = CustomUserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = '👤 کاربر'
        verbose_name_plural = '👤 کاربران'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        name = self.full_name or self.phone
        return name

    # ═══════════ Properties ═══════════

    @property
    def full_name(self):
        """نام کامل"""
        if self.first_name or self.last_name:
            return f'{self.first_name} {self.last_name}'.strip()
        return self.verified_name or self.phone

    @property
    def display_name(self):
        """نام نمایشی کاربر"""
        return self.full_name

    @property
    def has_business(self):
        """آیا کاربر کسب‌وکار دارد؟"""
        return hasattr(self, 'businesses') and self.businesses.exists()

    def get_short_name(self):
        return self.first_name or self.phone

    def get_full_name(self):
        return self.full_name


class OtpCode(models.Model):
    """کد تایید OTP"""

    class Purpose(models.TextChoices):
        LOGIN = 'login', 'ورود'
        ADMIN_LOGIN = 'admin_login', 'ورود پنل مدیریت' 
        CHANGE_PHONE = 'change_phone', 'تغییر شماره'
        BOOKING_VERIFY = 'booking_verify', 'تایید رزرو'
        DELETE_ACCOUNT = 'delete_account', 'حذف حساب'

    phone = models.CharField(
        'شماره موبایل',
        max_length=11,
        db_index=True,
    )
    code = models.CharField(
        'کد تایید',
        max_length=5,
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
    expires_at = models.DateTimeField(
        'تاریخ انقضا',
    )
    created_at = models.DateTimeField(
        'تاریخ ایجاد',
        auto_now_add=True,
    )

    class Meta:
        db_table = 'otp_codes'
        verbose_name = '🔑 کد تایید'
        verbose_name_plural = '🔑 کدهای تایید'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'purpose']),
        ]

    def __str__(self):
        return f'OTP for {self.phone} ({self.purpose})'

    @classmethod
    def generate_code(cls):
        """تولید کد ۵ رقمی تصادفی"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(5)])

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def verify(self, entered_code):
        """بررسی صحت کد"""
        if self.code == entered_code and self.is_valid:
            self.is_used = True
            self.save(update_fields=['is_used'])
            return True
        return False


class UserDevice(models.Model):
    """دستگاه‌های فعال کاربر (برای آینده)"""

    class DeviceType(models.TextChoices):
        IOS = 'ios', 'آیفون'
        ANDROID = 'android', 'اندروید'
        DESKTOP = 'desktop', 'دسکتاپ'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='devices',
        verbose_name='کاربر',
    )
    device_name = models.CharField(
        'نام دستگاه',
        max_length=100,
    )
    device_type = models.CharField(
        'نوع دستگاه',
        max_length=20,
        choices=DeviceType.choices,
    )
    os_info = models.CharField(
        'اطلاعات سیستم‌عامل',
        max_length=100,
    )
    ip_address = models.GenericIPAddressField(
        'آی‌پی',
    )
    location = models.CharField(
        'موقعیت',
        max_length=100,
    )
    is_current = models.BooleanField(
        'دستگاه فعلی',
        default=False,
    )
    last_active = models.DateTimeField(
        'آخرین فعالیت',
        auto_now=True,
    )

    class Meta:
        db_table = 'user_devices'
        verbose_name = '📱 دستگاه فعال'
        verbose_name_plural = '📱 دستگاه‌های فعال'
        ordering = ['-last_active']

    def __str__(self):
        return f'{self.device_name} - {self.user.phone}'


class UserReferral(models.Model):
    """کد معرف — غیرفعال در فاز ۱ ولی مدل آماده باشد"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='referral',
        verbose_name='کاربر',
    )
    referral_code = models.CharField(
        'کد معرف',
        max_length=20,
        unique=True,
    )
    referred_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='referred_users',
        on_delete=models.SET_NULL,
        verbose_name='معرف',
    )
    is_active = models.BooleanField(
        'فعال',
        default=False,  # غیرفعال در فاز ۱
    )

    class Meta:
        db_table = 'user_referrals'
        verbose_name = '🎫 کد معرف'
        verbose_name_plural = '🎫 کدهای معرف'

    def __str__(self):
        return f'{self.user.phone} - {self.referral_code}'


class UserBankInfo(models.Model):
    """
    اطلاعات بانکی کاربر برای استرداد وجه
    🆕 فاز ۳
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='bank_info',
        verbose_name='کاربر',
    )
    bank_name = models.CharField(
        'نام بانک',
        max_length=100,
        blank=True,
        default='',
    )
    bank_id = models.CharField(
        'شناسه بانک',
        max_length=20,
        blank=True,
        default='',
    )
    sheba = models.CharField(
        'شماره شبا',
        max_length=26,
        blank=True,
        default='',
    )
    card_number = models.CharField(
        'شماره کارت',
        max_length=16,
        blank=True,
        default='',
    )
    owner_name = models.CharField(
        'نام صاحب حساب',
        max_length=100,
        blank=True,
        default='',
    )
    is_complete = models.BooleanField(
        'اطلاعات کامل است',
        default=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_bank_info'
        verbose_name = '🏦 اطلاعات بانکی کاربر'
        verbose_name_plural = '🏦 اطلاعات بانکی کاربران'

    def __str__(self):
        return f'{self.user.phone} - {self.bank_name}'

    def check_completeness(self):
        """بررسی کامل بودن اطلاعات"""
        self.is_complete = bool(
            self.bank_name and
            self.sheba and
            len(self.sheba) == 26 and
            self.card_number and
            len(self.card_number) == 16 and
            self.owner_name
        )
        return self.is_complete

    def save(self, *args, **kwargs):
        self.check_completeness()
        super().save(*args, **kwargs)