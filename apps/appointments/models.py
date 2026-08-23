"""
نوبت‌ها و رزرو — با تاریخ جلالی
بدون تیم
"""
import random
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import BaseModel


class Appointment(BaseModel):
    """نوبت رزرو شده"""

    class Status(models.TextChoices):
        RESERVED = 'reserved', 'رزرو شده'
        DONE = 'done', 'انجام شده'
        CANCELLED_BY_SALON = 'cancelled_by_salon', 'لغو توسط سالن'
        CANCELLED_BY_CUSTOMER = 'cancelled_by_customer', 'لغو توسط مشتری'

    # ═══════════ روابط ═══════════
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name='خدمت',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='مشتری',
    )
    # ❌ team_member حذف شد

    # ═══════════ تاریخ و ساعت (جلالی) ═══════════
    jy = models.IntegerField('سال جلالی')
    jm = models.IntegerField('ماه جلالی')
    jd = models.IntegerField('روز جلالی')
    date_key = models.CharField('کلید تاریخ', max_length=10)
    time_slot = models.TimeField('ساعت نوبت')

    # ═══════════ وضعیت ═══════════
    status = models.CharField(
        'وضعیت',
        max_length=30,
        choices=Status.choices,
        default=Status.RESERVED,
        db_index=True,
    )

    # ═══════════ تایید ═══════════
    verification_code = models.CharField('کد تایید ۴ رقمی', max_length=4, blank=True, default='')
    is_trust_based = models.BooleanField('اعتماد به سالن', default=False)
    is_verified = models.BooleanField('تایید شده', default=False)
    verified_at = models.DateTimeField('زمان تایید', null=True, blank=True)

    # ═══════════ لغو ═══════════
    cancellation_reason = models.TextField('دلیل لغو', blank=True, default='')
    cancelled_at = models.DateTimeField('زمان لغو', null=True, blank=True)

    # ═══════════ مالی ═══════════
    total_price = models.BigIntegerField('قیمت کل (تومان)')
    deposit_amount = models.BigIntegerField('مبلغ بیعانه (تومان)', default=0)
    remaining_amount = models.BigIntegerField('مبلغ باقی‌مانده (تومان)', default=0)

    # ═══════════ یادآوری ═══════════
    reminder_sent = models.BooleanField('یادآوری ارسال شده', default=False)
    reminder_sent_at = models.DateTimeField('زمان ارسال یادآوری', null=True, blank=True)

    # ═══════════ نظردهی ═══════════
    has_review = models.BooleanField('نظر ثبت شده', default=False)

    class Meta:
        db_table = 'appointments'
        verbose_name = '📅 نوبت'
        verbose_name_plural = '📅 نوبت‌ها'
        ordering = ['-jy', '-jm', '-jd', 'time_slot']
        indexes = [
            models.Index(fields=['business', 'date_key']),
            models.Index(fields=['customer', 'status']),
        ]

    def __str__(self):
        return f'{self.customer.phone} - {self.service.name} ({self.date_key})'

    def save(self, *args, **kwargs):
        self.date_key = f'{self.jy}/{self.jm:02d}/{self.jd:02d}'
        # ✅ فاز ۳: فقط برای نوبت‌های غیراعتمادی کد تولید شود
        # نوبت‌های اعتمادی کد ثابت '0000' دارند
        if (
            not self.verification_code
            and self.status == self.Status.RESERVED
            and not self.is_trust_based  # ✅ شرط جدید
        ):
            self.verification_code = self.generate_verification_code()
        self.remaining_amount = self.total_price - self.deposit_amount
        super().save(*args, **kwargs)
        

    def generate_verification_code(self):
        return ''.join([str(random.randint(0, 9)) for _ in range(4)])

    def cancel_by_customer(self, reason=''):
        """لغو توسط مشتری — استرداد کامل (هماهنگ با فرانت)"""
        from apps.payments.services import process_refund

        self.status = self.Status.CANCELLED_BY_CUSTOMER
        self.cancellation_reason = reason
        self.cancelled_at = timezone.now()
        self.save()

        if self.deposit_amount > 0:
            process_refund(self)

    def cancel_by_salon(self, reason=''):
        from apps.payments.services import process_refund
        self.status = self.Status.CANCELLED_BY_SALON
        self.cancellation_reason = reason
        self.cancelled_at = timezone.now()
        self.save()
        if self.deposit_amount > 0:
            process_refund(self, full_amount=True)