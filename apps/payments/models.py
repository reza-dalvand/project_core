"""
مدل‌های مالی و پرداخت
- Wallet: کیف پول کاربران و کسب‌وکارها
- BankAccount: اطلاعات حساب بانکی صاحبان کسب‌وکار
- Transaction: تراکنش‌ها (بیعانه، پرداخت کامل، استرداد، تسویه)
- Settlement: درخواست‌های تسویه حساب
- RefundRequest: درخواست‌های استرداد وجه
"""
import random
import string
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone


def generate_tracking_code():
    """تولید کد پیگیری ۱۰ رقمی"""
    return 'TRK-' + ''.join(random.choices(string.digits, k=10))


def generate_ref_number():
    """تولید شماره ارجاع"""
    now = timezone.now()
    return f"REF-{now.year}-{random.randint(100000, 999999)}"


# ═══════════════════════════════════════════════════════════════
#                    کیف پول
# ═══════════════════════════════════════════════════════════════
class Wallet(models.Model):
    """کیف پول کاربر یا کسب‌وکار"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name='کاربر',
    )
    balance = models.PositiveBigIntegerField(
        'موجودی (تومان)',
        default=0,
        validators=[MinValueValidator(0)],
    )
    total_credit = models.PositiveBigIntegerField(
        'مجموع واریزی‌ها',
        default=0,
    )
    total_debit = models.PositiveBigIntegerField(
        'مجموع برداشت‌ها',
        default=0,
    )
    is_frozen = models.BooleanField(
        'مسدود',
        default=False,
        help_text='در صورت مسدود بودن، امکان برداشت وجود ندارد',
    )
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '👛 کیف پول'
        verbose_name_plural = '👛 کیف پول‌ها'

    def __str__(self):
        return f'کیف پول {self.user.phone} - {self.balance:,} تومان'

    def deposit(self, amount, description=''):
        """واریز به کیف پول"""
        from apps.payments.models import WalletTransaction
        self.balance += amount
        self.total_credit += amount
        self.save(update_fields=['balance', 'total_credit', 'updated_at'])
        return WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            type=WalletTransaction.Type.DEPOSIT,
            description=description,
            balance_after=self.balance,
        )

    def withdraw(self, amount, description=''):
        """برداشت از کیف پول"""
        from apps.payments.models import WalletTransaction
        if self.is_frozen:
            raise ValueError('کیف پول مسدود است')
        if self.balance < amount:
            raise ValueError('موجودی کافی نیست')
        self.balance -= amount
        self.total_debit += amount
        self.save(update_fields=['balance', 'total_debit', 'updated_at'])
        return WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            type=WalletTransaction.Type.WITHDRAWAL,
            description=description,
            balance_after=self.balance,
        )


class WalletTransaction(models.Model):
    """تراکنش‌های کیف پول"""

    class Type(models.TextChoices):
        DEPOSIT = 'deposit', 'واریز'
        WITHDRAWAL = 'withdrawal', 'برداشت'
        REFUND = 'refund', 'استرداد'
        SETTLEMENT = 'settlement', 'تسویه'

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='کیف پول',
    )
    amount = models.PositiveBigIntegerField('مبلغ (تومان)')
    type = models.CharField(
        'نوع تراکنش',
        max_length=20,
        choices=Type.choices,
    )
    description = models.CharField('توضیحات', max_length=300, blank=True, default='')
    balance_after = models.PositiveBigIntegerField('موجودی پس از تراکنش', default=0)
    reference = models.CharField(
        'ارجاع (مثلاً ID تراکنش اصلی)',
        max_length=100,
        blank=True,
        default='',
    )
    created_at = models.DateTimeField('تاریخ', auto_now_add=True)

    class Meta:
        verbose_name = '📋 تراکنش کیف پول'
        verbose_name_plural = '📋 تراکنش‌های کیف پول'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_type_display()} - {self.amount:,} تومان'


# ═══════════════════════════════════════════════════════════════
#                    حساب بانکی
# ═══════════════════════════════════════════════════════════════
class BankAccount(models.Model):
    """اطلاعات حساب بانکی صاحب کسب‌وکار"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار تایید'
        VERIFIED = 'verified', 'تایید شده'
        REJECTED = 'rejected', 'رد شده'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_accounts',
        verbose_name='کاربر',
    )
    business = models.OneToOneField(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='bank_account',
        verbose_name='کسب‌وکار',
        null=True,
        blank=True,
    )
    owner_name = models.CharField('نام صاحب حساب', max_length=150)
    national_id = models.CharField('کد ملی صاحب حساب', max_length=10)
    bank_name = models.CharField('نام بانک', max_length=100)
    sheba = models.CharField('شماره شبا', max_length=26)
    card_number = models.CharField('شماره کارت', max_length=16)
    account_number = models.CharField('شماره حساب', max_length=30, blank=True, default='')
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    is_active = models.BooleanField('فعال (پیش‌فرض)', default=False)
    rejection_reason = models.TextField('دلیل رد', blank=True, default='')
    verified_at = models.DateTimeField('تاریخ تایید', null=True, blank=True)
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '🏦 حساب بانکی'
        verbose_name_plural = '🏦 حساب‌های بانکی'
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f'{self.owner_name} - {self.bank_name} - {self.get_status_display()}'


# ═══════════════════════════════════════════════════════════════
#                    تراکنش اصلی
# ═══════════════════════════════════════════════════════════════
class Transaction(models.Model):
    """تراکنش‌های اصلی سیستم"""

    class Type(models.TextChoices):
        DEPOSIT = 'deposit', 'بیعانه'
        FULL_PAYMENT = 'full_payment', 'پرداخت کامل'
        SETTLEMENT = 'settlement', 'تسویه با کسب‌وکار'
        REFUND = 'refund', 'استرداد'
        WALLET_TOPUP = 'wallet_topup', 'شارژ کیف پول'

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار پرداخت'
        SUCCESS = 'success', 'موفق'
        FAILED = 'failed', 'ناموفق'
        CANCELLED = 'cancelled', 'لغو شده'
        REFUNDED = 'refunded', 'مسترد شده'
        SETTLING = 'settling', 'در حال تسویه'
        SETTLED = 'settled', 'تسویه شده'

    class Gateway(models.TextChoices):
        ZARINPAL = 'zarinpal', 'زرین‌پال'
        IDPAY = 'idpay', 'آی‌دی‌پی'
        MELAT = 'melat', 'بانک ملت'
        WALLET = 'wallet', 'کیف پول'

    # ─── اطلاعات اصلی ───
    tracking_code = models.CharField(
        'کد پیگیری',
        max_length=20,
        unique=True,
        default=generate_tracking_code,
    )
    ref_number = models.CharField(
        'شماره ارجاع',
        max_length=30,
        unique=True,
        default=generate_ref_number,
    )

    # ─── روابط ───
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='کاربر',
    )
    appointment = models.ForeignKey(
        'bookings.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='نوبت',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='کسب‌وکار',
    )

    # ─── نوع و مبلغ ───
    type = models.CharField('نوع', max_length=20, choices=Type.choices)
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    amount = models.PositiveBigIntegerField('مبلغ (تومان)')
    original_price = models.PositiveBigIntegerField(
        'قیمت اصلی خدمت',
        default=0,
    )
    discount_amount = models.PositiveBigIntegerField(
        'مبلغ تخفیف',
        default=0,
    )
    commission_amount = models.PositiveBigIntegerField(
        'کارمزد زیبانو (تومان)',
        default=0,
        help_text='کارمزد ۵٪ که توسط زیبانو کسر می‌شود',
    )
    net_amount = models.PositiveBigIntegerField(
        'مبلغ خالص (تومان)',
        default=0,
        help_text='مبلغ پس از کسر کارمزد',
    )

    # ─── درگاه ───
    gateway = models.CharField(
        'درگاه پرداخت',
        max_length=20,
        choices=Gateway.choices,
        blank=True,
        default='',
    )
    gateway_ref_id = models.CharField(
        'Ref ID درگاه',
        max_length=100,
        blank=True,
        default='',
    )
    card_number = models.CharField(
        'شماره کارت پرداخت‌کننده',
        max_length=16,
        blank=True,
        default='',
    )
    card_bank = models.CharField(
        'بانک کارت',
        max_length=50,
        blank=True,
        default='',
    )

    # ─── اطلاعات تکمیلی ───
    failure_reason = models.TextField('دلیل شکست', blank=True, default='')
    description = models.CharField('توضیحات', max_length=300, blank=True, default='')
    ip_address = models.GenericIPAddressField('آی‌پی', null=True, blank=True)

    # ─── تاریخ‌ها ───
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    paid_at = models.DateTimeField('تاریخ پرداخت', null=True, blank=True)
    settled_at = models.DateTimeField('تاریخ تسویه', null=True, blank=True)
    refunded_at = models.DateTimeField('تاریخ استرداد', null=True, blank=True)

    class Meta:
        verbose_name = '💰 تراکنش'
        verbose_name_plural = '💰 تراکنش‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['business', 'status']),
            models.Index(fields=['tracking_code']),
            models.Index(fields=['type', 'status']),
        ]

    def __str__(self):
        return f'{self.tracking_code} - {self.get_type_display()} - {self.amount:,} تومان'

    def save(self, *args, **kwargs):
        # محاسبه کارمزد و مبلغ خالص اگر هنوز محاسبه نشده
        if self.amount > 0 and self.commission_amount == 0 and self.type in [self.Type.DEPOSIT, self.Type.FULL_PAYMENT]:
            self.commission_amount = int(self.amount * 0.05)  # ۵٪ کارمزد
            self.net_amount = self.amount - self.commission_amount
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════
#                    تسویه حساب
# ═══════════════════════════════════════════════════════════════
class Settlement(models.Model):
    """درخواست تسویه حساب با کسب‌وکار"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        PROCESSING = 'processing', 'در حال پردازش'
        COMPLETED = 'completed', 'انجام شده'
        REJECTED = 'rejected', 'رد شده'

    class Frequency(models.TextChoices):
        MANUAL = 'manual', 'دستی'
        DAILY = 'daily', 'روزانه'
        WEEKLY = 'weekly', 'هفتگی'

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='settlements',
        verbose_name='کسب‌وکار',
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.PROTECT,
        related_name='settlements',
        verbose_name='حساب بانکی',
    )
    amount = models.PositiveBigIntegerField('مبلغ تسویه (تومان)')
    commission_total = models.PositiveBigIntegerField(
        'مجموع کارمزد کسر شده',
        default=0,
    )
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    frequency = models.CharField(
        'نوع تسویه',
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.MANUAL,
    )
    transactions_included = models.ManyToManyField(
        Transaction,
        related_name='settlements',
        verbose_name='تراکنش‌های شامل تسویه',
        blank=True,
    )
    bank_ref_code = models.CharField(
        'کد پیگیری بانکی',
        max_length=50,
        blank=True,
        default='',
    )
    rejection_reason = models.TextField('دلیل رد', blank=True, default='')
    requested_at = models.DateTimeField('تاریخ درخواست', auto_now_add=True)
    processed_at = models.DateTimeField('تاریخ پردازش', null=True, blank=True)
    completed_at = models.DateTimeField('تاریخ تکمیل', null=True, blank=True)

    class Meta:
        verbose_name = '🏧 تسویه حساب'
        verbose_name_plural = '🏧 تسویه حساب‌ها'
        ordering = ['-requested_at']

    def __str__(self):
        return f'تسویه {self.business.name} - {self.amount:,} تومان - {self.get_status_display()}'


# ═══════════════════════════════════════════════════════════════
#                    درخواست استرداد
# ═══════════════════════════════════════════════════════════════
class RefundRequest(models.Model):
    """درخواست استرداد وجه"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        APPROVED = 'approved', 'تایید شده'
        REJECTED = 'rejected', 'رد شده'
        REFUNDED = 'refunded', 'مسترد شده'

    class Reason(models.TextChoices):
        CANCELLED_BY_BUSINESS = 'cancelled_by_business', 'لغو توسط کسب‌وکار'
        CANCELLED_BY_CUSTOMER = 'cancelled_by_customer', 'لغو توسط مشتری (طبق قوانین)'
        NO_SHOW = 'no_show', 'عدم حضور مشتری (جریمه)'
        DOUBLE_BOOKING = 'double_booking', 'رزرو تکراری'
        TECHNICAL_ERROR = 'technical_error', 'خطای فنی'

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='refund_requests',
        verbose_name='تراکنش اصلی',
    )
    appointment = models.ForeignKey(
        'bookings.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refund_requests',
        verbose_name='نوبت',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='refund_requests',
        verbose_name='درخواست‌دهنده',
    )
    amount = models.PositiveBigIntegerField('مبلغ استرداد (تومان)')
    penalty_amount = models.PositiveBigIntegerField(
        'مبلغ جریمه (تومان)',
        default=0,
    )
    reason = models.CharField(
        'دلیل استرداد',
        max_length=30,
        choices=Reason.choices,
    )
    reason_text = models.TextField('توضیحات', blank=True, default='')
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_refunds',
        verbose_name='بررسی‌کننده',
    )
    refund_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refund_of',
        verbose_name='تراکنش استرداد',
    )
    requested_at = models.DateTimeField('تاریخ درخواست', auto_now_add=True)
    reviewed_at = models.DateTimeField('تاریخ بررسی', null=True, blank=True)
    refunded_at = models.DateTimeField('تاریخ استرداد', null=True, blank=True)

    class Meta:
        verbose_name = '🔄 درخواست استرداد'
        verbose_name_plural = '🔄 درخواست‌های استرداد'
        ordering = ['-requested_at']

    def __str__(self):
        return f'استرداد {self.amount:,} تومان - {self.get_status_display()}'