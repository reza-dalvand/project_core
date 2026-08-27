"""
پشتیبانی و FAQ
"""
from django.db import models
from django.conf import settings

from apps.core.models import BaseModel


class FAQ(BaseModel):
    """سوالات متداول"""

    question = models.CharField('سوال', max_length=300)
    answer = models.TextField('پاسخ')
    category = models.CharField('دسته‌بندی', max_length=50, blank=True, default='')
    sort_order = models.IntegerField('ترتیب', default=0)

    class Meta:
        db_table = 'faqs'
        verbose_name = '❓ سوال متداول'
        verbose_name_plural = '❓ سوالات متداول'
        ordering = ['sort_order']

    def __str__(self):
        return self.question


class SupportTicket(BaseModel):
    """تیکت پشتیبانی"""

    class Status(models.TextChoices):
        OPEN = 'open', 'باز'
        IN_PROGRESS = 'in_progress', 'در حال بررسی'
        RESOLVED = 'resolved', 'حل شده'
        CLOSED = 'closed', 'بسته شده'

    class Priority(models.TextChoices):
        LOW = 'low', 'کم'
        MEDIUM = 'medium', 'متوسط'
        HIGH = 'high', 'بالا'
        URGENT = 'urgent', 'فوری'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
        verbose_name='کاربر',
    )
    subject = models.CharField('موضوع', max_length=200)
    message = models.TextField('پیام')
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    priority = models.CharField(
        'اولویت',
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    response = models.TextField('پاسخ پشتیبانی', blank=True, default='')
    responded_at = models.DateTimeField('زمان پاسخ', null=True, blank=True)

    class Meta:
        db_table = 'support_tickets'
        verbose_name = '🎧 تیکت پشتیبانی'
        verbose_name_plural = '🎧 تیکت‌های پشتیبانی'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.phone} - {self.subject}'