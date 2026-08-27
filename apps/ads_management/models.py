"""
مدیریت تبلیغات (برای آینده - فقط مدل)
"""
from django.db import models

from apps.core.models import BaseModel


class AdCampaign(BaseModel):
    """کمپین تبلیغاتی"""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'پیش‌نویس'
        ACTIVE = 'active', 'فعال'
        PAUSED = 'paused', 'متوقف'
        ENDED = 'ended', 'پایان یافته'

    name = models.CharField('نام کمپین', max_length=100)
    description = models.TextField('توضیحات', blank=True, default='')
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    start_date = models.DateTimeField('تاریخ شروع', null=True, blank=True)
    end_date = models.DateTimeField('تاریخ پایان', null=True, blank=True)
    budget = models.BigIntegerField('بودجه (تومان)', default=0)
    spent = models.BigIntegerField('مبلغ خرج شده (تومان)', default=0)
    impressions = models.IntegerField('تعداد نمایش', default=0)
    clicks = models.IntegerField('تعداد کلیک', default=0)

    class Meta:
        db_table = 'ad_campaigns'
        verbose_name = '📊 کمپین تبلیغاتی'
        verbose_name_plural = '📊 کمپین‌های تبلیغاتی'
        ordering = ['-created_at']

    def __str__(self):
        return self.name