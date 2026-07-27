"""
مدل‌های نوبت‌دهی
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Schedule(models.Model):
    """برنامه کاری روزانه کسب‌وکار"""

    class WeekDay(models.IntegerChoices):
        SATURDAY = 0, 'شنبه'
        SUNDAY = 1, 'یکشنبه'
        MONDAY = 2, 'دوشنبه'
        TUESDAY = 3, 'سه‌شنبه'
        WEDNESDAY = 4, 'چهارشنبه'
        THURSDAY = 5, 'پنجشنبه'
        FRIDAY = 6, 'جمعه'

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        'businesses.Service',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='خدمت',
        null=True,
        blank=True,
    )

    weekday = models.PositiveSmallIntegerField(
        'روز هفته',
        choices=WeekDay.choices,
    )
    is_working = models.BooleanField('روز کاری', default=True)
    start_time = models.TimeField('ساعت شروع', null=True, blank=True)
    end_time = models.TimeField('ساعت پایان', null=True, blank=True)
    slot_duration = models.PositiveIntegerField(
        'مدت هر نوبت (دقیقه)',
        default=30,
        validators=[MinValueValidator(15), MaxValueValidator(120)],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '🕐 برنامه کاری'
        verbose_name_plural = '🕐 برنامه‌های کاری'
        unique_together = [('business', 'weekday')]
        ordering = ['weekday']

    def __str__(self):
        return f'{self.business.name} - {self.get_weekday_display()}'


class ScheduleBreak(models.Model):
    """بازه استراحت در برنامه کاری"""

    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name='breaks',
        verbose_name='برنامه کاری',
    )
    start_time = models.TimeField('شروع استراحت')
    end_time = models.TimeField('پایان استراحت')

    class Meta:
        verbose_name = '☕ بازه استراحت'
        verbose_name_plural = '☕ بازه‌های استراحت'
        ordering = ['start_time']

    def __str__(self):
        return f'{self.schedule} - استراحت {self.start_time} تا {self.end_time}'


class TimeSlot(models.Model):
    """اسلات زمانی قابل رزرو"""

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'آزاد'
        BOOKED = 'booked', 'رزرو شده'
        BLOCKED = 'blocked', 'مسدود'
        EXPIRED = 'expired', 'منقضی'

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='time_slots',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        'businesses.Service',
        on_delete=models.CASCADE,
        related_name='time_slots',
        verbose_name='خدمت',
    )
    date = models.DateField('تاریخ')
    start_time = models.TimeField('ساعت شروع')
    end_time = models.TimeField('ساعت پایان')
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    class Meta:
        verbose_name = '⏰ اسلات زمانی'
        verbose_name_plural = '⏰ اسلات‌های زمانی'
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['business', 'date', 'status']),
            models.Index(fields=['service', 'date']),
        ]

    def __str__(self):
        return f'{self.business.name} - {self.date} {self.start_time}'


class Appointment(models.Model):
    """نوبت رزرو شده"""

    class Status(models.TextChoices):
        RESERVED = 'reserved', 'رزرو شده'
        CONFIRMED = 'confirmed', 'تایید شده'
        IN_PROGRESS = 'in_progress', 'در حال انجام'
        DONE = 'done', 'انجام شده'
        CANCELLED_BY_CUSTOMER = 'cancelled_by_customer', 'لغو توسط مشتری'
        CANCELLED_BY_SALON = 'cancelled_by_salon', 'لغو توسط سالن'
        NO_SHOW = 'no_show', 'عدم مراجعه'

    # ─── روابط ───
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='مشتری',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        'businesses.Service',
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name='خدمت',
    )
    employee = models.ForeignKey(
        'businesses.Employee',
        on_delete=models.SET_NULL,
        related_name='appointments',
        verbose_name='کارمند ارائه‌دهنده',
        null=True,
        blank=True,
    )
    time_slot = models.OneToOneField(
        TimeSlot,
        on_delete=models.SET_NULL,
        related_name='appointment',
        verbose_name='اسلات زمانی',
        null=True,
        blank=True,
    )

    # ─── اطلاعات نوبت ───
    date = models.DateField('تاریخ نوبت')
    time = models.TimeField('ساعت نوبت')
    status = models.CharField(
        'وضعیت',
        max_length=30,
        choices=Status.choices,
        default=Status.RESERVED,
        db_index=True,
    )

    # ─── مالی ───
    original_price = models.PositiveIntegerField('قیمت اصلی (تومان)')
    discount_percent = models.PositiveIntegerField('درصد تخفیف', default=0)
    final_price = models.PositiveIntegerField('قیمت نهایی (تومان)')
    deposit_amount = models.PositiveIntegerField('مبلغ بیعانه (تومان)', default=0)
    deposit_paid = models.BooleanField('بیعانه پرداخت شده', default=False)

    # ─── کد تایید ───
    verification_code = models.CharField(
        'کد تایید ۴ رقمی',
        max_length=4,
        blank=True,
    )
    code_generated_at = models.DateTimeField(
        'زمان تولید کد',
        null=True,
        blank=True,
    )

    # ─── لغو ───
    cancellation_reason = models.TextField('دلیل لغو', blank=True, default='')
    cancelled_at = models.DateTimeField('زمان لغو', null=True, blank=True)

    # ─── انجام ───
    verified_at = models.DateTimeField('زمان تایید انجام', null=True, blank=True)

    # ─── تاریخ‌ها ───
    created_at = models.DateTimeField('تاریخ رزرو', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '📅 نوبت'
        verbose_name_plural = '📅 نوبت‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['business', 'date', 'status']),
            models.Index(fields=['date', 'time']),
        ]

    def __str__(self):
        return f'{self.customer.phone} - {self.service.name} ({self.date})'

    def save(self, *args, **kwargs):
        # تولید کد تایید ۴ رقمی
        if not self.verification_code and self.status == self.Status.RESERVED:
            import random
            self.verification_code = str(random.randint(1000, 9999))
            from django.utils import timezone
            self.code_generated_at = timezone.now()
        super().save(*args, **kwargs)


class CancellationRequest(models.Model):
    """درخواست لغو نوبت"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        APPROVED = 'approved', 'تایید شده'
        REJECTED = 'rejected', 'رد شده'

    class Reason(models.TextChoices):
        CUSTOMER_REQUEST = 'customer_request', 'درخواست مشتری'
        SALON_CLOSED = 'salon_closed', 'تعطیلی سالن'
        EMPLOYEE_UNAVAILABLE = 'employee_unavailable', 'عدم حضور کارمند'
        TECHNICAL_ISSUE = 'technical_issue', 'مشکل فنی'
        OTHER = 'other', 'سایر'

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='cancellation_request',
        verbose_name='نوبت',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cancellation_requests',
        verbose_name='درخواست‌دهنده',
    )
    reason_type = models.CharField(
        'نوع دلیل',
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
    refund_amount = models.PositiveIntegerField(
        'مبلغ استرداد (تومان)',
        default=0,
    )
    penalty_amount = models.PositiveIntegerField(
        'مبلغ جریمه (تومان)',
        default=0,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_cancellations',
        verbose_name='بررسی‌کننده',
    )
    reviewed_at = models.DateTimeField('زمان بررسی', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '❌ درخواست لغو'
        verbose_name_plural = '❌ درخواست‌های لغو'
        ordering = ['-created_at']

    def __str__(self):
        return f'لغو نوبت {self.appointment.id} - {self.get_status_display()}'