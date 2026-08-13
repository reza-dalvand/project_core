# apps/services/models.py
"""
خدمات کسب‌وکارها + لیست قیمت
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
    original_price = models.BigIntegerField('قیمت اصلی (تومان)')
    discount_percent = models.IntegerField('درصد تخفیف', default=0)
    has_deposit = models.BooleanField('نیاز به بیعانه', default=False)
    deposit_amount = models.BigIntegerField('مبلغ بیعانه (تومان)', default=0)
    duration = models.IntegerField('مدت زمان (دقیقه)', default=60)
    renewal_days = models.IntegerField('یادآوری تمدید (روز)', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        db_table = 'services'
        verbose_name = '💆 خدمت'
        verbose_name_plural = '💆 خدمات'
        ordering = ['business', 'name']

    def __str__(self):
        return f'{self.business.name} - {self.name}'

    @property
    def discount_amount(self):
        return round(self.original_price * self.discount_percent / 100)

    @property
    def final_price(self):
        return self.original_price - self.discount_amount

    @property
    def app_fee(self):
        from apps.core.utils import calculate_app_fee
        return calculate_app_fee(self.final_price)

    def clean(self):
        if self.has_deposit and self.deposit_amount > self.final_price:
            raise ValidationError('مبلغ بیعانه نمی‌تواند بیشتر از قیمت نهایی باشد')


# ═══════════════════════════════════════════════
#    مدل‌های جدید: لیست قیمت
# ═══════════════════════════════════════════════

class PriceList(BaseModel):
    """لیست قیمت خدمات یک کسب‌وکار"""

    class ThemeChoices(models.TextChoices):
        ROSE = 'rose', 'صورتی پاستلی'
        GOLD = 'gold', 'طلایی لوکس'
        MINT = 'mint', 'سبز مینیمال'
        CLASSIC = 'classic', 'کلاسیک'

    business = models.OneToOneField(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='price_list',
        verbose_name='کسب‌وکار',
    )
    theme = models.CharField(
        'تم ظاهری',
        max_length=20,
        choices=ThemeChoices.choices,
        default=ThemeChoices.CLASSIC,
    )
    is_published = models.BooleanField('منتشر شده', default=False)

    class Meta:
        db_table = 'price_lists'
        verbose_name = '📋 لیست قیمت'
        verbose_name_plural = '📋 لیست‌های قیمت'

    def __str__(self):
        return f'لیست قیمت {self.business.name}'


class PriceListNote(BaseModel):
    """یادداشت‌های لیست قیمت (مثل افزانه مواد)"""
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name='لیست قیمت',
    )
    label = models.CharField('عنوان', max_length=100)
    min_value = models.IntegerField('حداقل', default=0)
    max_value = models.IntegerField('حداکثر', default=0)

    class Meta:
        db_table = 'price_list_notes'
        verbose_name = '📝 یادداشت لیست قیمت'
        verbose_name_plural = '📝 یادداشت‌های لیست قیمت'
        ordering = ['created_at']

    def __str__(self):
        return self.label