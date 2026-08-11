"""
خدمات کسب‌وکارها
"""
from django.db import models
from django.core.exceptions import ValidationError

from apps.core.models import BaseModel


class Service(BaseModel):
    """خدمت کسب‌وکار"""

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name='کسب‌وکار',
    )
    name = models.CharField('نام خدمت', max_length=100)
    category = models.ForeignKey(
        'categories.ServiceCategory',
        on_delete=models.PROTECT,
        related_name='services',
        verbose_name='دسته‌بندی',
    )
    sub_service = models.ForeignKey(
        'categories.SubService',
        on_delete=models.PROTECT,
        related_name='services',
        verbose_name='زیرخدمت',
    )
    description = models.TextField('توضیحات', blank=True, max_length=300, default='')

    # ═══════════ قیمت‌گذاری ═══════════
    original_price = models.BigIntegerField('قیمت اصلی (تومان)')
    discount_percent = models.IntegerField('درصد تخفیف', default=0)

    # ═══════════ بیعانه ═══════════
    has_deposit = models.BooleanField('نیاز به بیعانه', default=False)
    deposit_amount = models.BigIntegerField('مبلغ بیعانه (تومان)', default=0)

    # ═══════════ زمان ═══════════
    duration = models.IntegerField('مدت زمان (دقیقه)', default=60)

    # ═══════════ یادآوری تمدید ═══════════
    renewal_days = models.IntegerField('یادآوری تمدید (روز)', default=0)

    # ═══════════ وضعیت ═══════════
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        db_table = 'services'
        verbose_name = '💆 خدمت'
        verbose_name_plural = '💆 خدمات'
        ordering = ['business', 'name']

    def __str__(self):
        return f'{self.business.name} - {self.name}'

    # ═══════════ Properties ═══════════

    @property
    def discount_amount(self):
        """مبلغ تخفیف"""
        return round(self.original_price * self.discount_percent / 100)

    @property
    def final_price(self):
        """قیمت نهایی"""
        return self.original_price - self.discount_amount

    @property
    def app_fee(self):
        """محاسبه کمیسیون زیبانو"""
        from apps.core.utils import calculate_app_fee
        return calculate_app_fee(self.final_price)

    def clean(self):
        if self.has_deposit and self.deposit_amount > self.final_price:
            raise ValidationError('مبلغ بیعانه نمی‌تواند بیشتر از قیمت نهایی باشد')