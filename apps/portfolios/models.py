"""
نمونه‌کارها
"""
from django.db import models
from django.core.exceptions import ValidationError

from apps.core.models import BaseModel


class Portfolio(BaseModel):
    """نمونه‌کار"""

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='portfolios',
        verbose_name='کسب‌وکار',
    )
    category = models.ForeignKey(
        'categories.ServiceCategory',
        on_delete=models.PROTECT,
        verbose_name='دسته‌بندی',
    )
    sub_service = models.ForeignKey(
        'categories.SubService',
        on_delete=models.PROTECT,
        verbose_name='زیرخدمت',
    )
    title = models.CharField('عنوان', max_length=100)
    description = models.TextField('توضیحات', blank=True, max_length=300, default='')
    cover_image = models.ImageField(
        'تصویر کاور',
        upload_to='portfolios/covers/',
    )

    class Meta:
        db_table = 'portfolios'
        verbose_name = '🖼️ نمونه‌کار'
        verbose_name_plural = '🖼️ نمونه‌کارها'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.business.name} - {self.title}'


class PortfolioImage(BaseModel):
    """تصاویر نمونه‌کار (حداکثر ۳ تصویر)"""

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='نمونه‌کار',
    )
    image = models.ImageField(
        'تصویر',
        upload_to='portfolios/images/',
    )
    sort_order = models.IntegerField('ترتیب', default=0)

    class Meta:
        db_table = 'portfolio_images'
        verbose_name = '📷 تصویر نمونه‌کار'
        verbose_name_plural = '📷 تصاویر نمونه‌کار'
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.portfolio.title} - تصویر {self.sort_order}'

    def clean(self):
        if not self.pk and self.portfolio.images.count() >= 3:
            raise ValidationError('حداکثر ۳ تصویر برای هر نمونه‌کار مجاز است')