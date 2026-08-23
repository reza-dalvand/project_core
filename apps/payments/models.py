"""
مدل‌های مالی و پرداخت — ساده‌سازی شده
"""
import random
import string
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.core.models import BaseModel
from apps.core.utils import generate_tracking_code, generate_ref_number


class Transaction(BaseModel):
    """تراکنش مالی"""

    class Type(models.TextChoices):
        DEPOSIT = 'deposit', 'بیعانه'
        FULL_PAYMENT = 'full_payment', 'پرداخت کامل'
        REFUND = 'refund', 'استرداد'
        SETTLEMENT = 'settlement', 'تسویه'

    class Status(models.TextChoices):
        BLOCKED = 'blocked', 'بلوکه (در انتظار خدمت)'
        SETTLING = 'settling', 'در حال تسویه'
        SETTLED = 'settled', 'تسویه شده'
        REFUNDED = 'refunded', 'مسترد به مشتری'
        FAILED = 'failed', 'ناموفق'

    # ═══════════ روابط ═══════════
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='کسب‌وکار',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='مشتری',
    )
    appointment = models.ForeignKey(
        'appointments.Appointment',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
        verbose_name='نوبت',
    )

    # ═══════════ نوع و مبلغ ═══════════
    type = models.CharField(
        'نوع',
        max_length=20,
        choices=Type.choices,
    )
    amount = models.BigIntegerField('مبلغ (تومان)')
    app_fee = models.BigIntegerField('کمیسیون بیو کلاب (تومان)', default=0)

    # ═══════════ وضعیت ═══════════
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.BLOCKED,
    )

    # ═══════════ درگاه پرداخت ═══════════
    gateway = models.CharField('درگاه پرداخت', max_length=50, default='zarinpal')
    gateway_transaction_id = models.CharField('شناسه تراکنش درگاه', max_length=100, blank=True, default='')
    tracking_code = models.CharField('کد پیگیری', max_length=50, blank=True, default='')
    ref_number = models.CharField('شماره ارجاع', max_length=50, blank=True, default='')

    # ═══════════ کارت ═══════════
    card_number = models.CharField('شماره کارت', max_length=20, blank=True, default='')
    card_bank = models.CharField('بانک کارت', max_length=50, blank=True, default='')

    # ═══════════ تسویه ═══════════
    settled_at = models.DateTimeField('تاریخ تسویه', null=True, blank=True)
    estimated_settlement = models.DateTimeField('تاریخ تخمینی تسویه', null=True, blank=True)

    # ═══════════ استرداد ═══════════
    refund_reason = models.TextField('دلیل استرداد', blank=True, default='')

    class Meta:
        db_table = 'transactions'
        verbose_name = '💰 تراکنش'
        verbose_name_plural = '💰 تراکنش‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'status']),
            models.Index(fields=['customer', 'status']),
        ]

    def __str__(self):
        return f'{self.tracking_code} - {self.get_type_display()} - {self.amount:,} تومان'

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = generate_tracking_code()
        if not self.ref_number:
            self.ref_number = generate_ref_number()
        super().save(*args, **kwargs)


class Settlement(BaseModel):
    """تسویه مالی به حساب کسب‌وکار"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        PROCESSING = 'processing', 'در حال واریز'
        COMPLETED = 'completed', 'واریز شده'
        FAILED = 'failed', 'ناموفق'

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='settlements',
        verbose_name='کسب‌وکار',
    )
    amount = models.BigIntegerField('مبلغ تسویه (تومان)')
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    bank_sheba = models.CharField('شماره شبا', max_length=26)
    bank_name = models.CharField('نام بانک', max_length=100)
    settled_at = models.DateTimeField('تاریخ تسویه', null=True, blank=True)

    class Meta:
        db_table = 'settlements'
        verbose_name = '🏧 تسویه حساب'
        verbose_name_plural = '🏧 تسویه حساب‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f'تسویه {self.business.name} - {self.amount:,} تومان'