"""
یادآوری تمدید خدمت
"""
from django.db import models
from django.conf import settings

from apps.core.models import BaseModel


class RenewalReminder(BaseModel):
    """یادآوری تمدید خدمت"""

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name='کسب‌وکار',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name='مشتری',
    )
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name='نوبت',
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        verbose_name='خدمت',
    )

    # ═══════════ تاریخ جلالی ═══════════
    last_service_date = models.CharField('تاریخ انجام خدمت', max_length=10)
    due_date = models.CharField('تاریخ موعد تمدید', max_length=10)
    days_remaining = models.IntegerField('روزهای باقی‌مانده')

    # ═══════════ وضعیت ارسال ═══════════
    reminder_sent = models.BooleanField('یادآوری ارسال شده', default=False)
    sent_date = models.CharField('تاریخ ارسال', max_length=10, blank=True, default='')
    has_new_booking_after_send = models.BooleanField('رزرو جدید پس از ارسال', default=False)

    class Meta:
        db_table = 'renewal_reminders'
        verbose_name = '🔔 یادآوری تمدید'
        verbose_name_plural = '🔔 یادآوری‌های تمدید'
        ordering = ['days_remaining']

    def __str__(self):
        return f'{self.customer.phone} - {self.service.name} - {self.days_remaining} روز'