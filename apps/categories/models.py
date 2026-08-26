"""
دسته‌بندی‌ها و زیرخدمات
"""
from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseModel


class ServiceCategory(BaseModel):
    """دسته‌بندی اصلی خدمات (میکاپ، ناخن، لیزر...)"""

    name = models.CharField('نام', max_length=50)
    slug = models.SlugField('اسلاگ', unique=True)
    icon_name = models.CharField(
        'آیکون',
        max_length=50,
        help_text='نام آیکون برای فرانت',
    )
    color = models.CharField('رنگ', max_length=7, default='#A88B7D')
    gradient_start = models.CharField('رنگ گرادیانت شروع', max_length=7, default='#A88B7D')
    gradient_end = models.CharField('رنگ گرادیانت پایان', max_length=7, default='#8D7468')
    sort_order = models.IntegerField('ترتیب', default=0)

    class Meta:
        db_table = 'service_categories'
        verbose_name = '🏷️ دسته‌بندی خدمات'
        verbose_name_plural = '🏷️ دسته‌بندی‌های خدمات'
        ordering = ['sort_order']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class SubService(BaseModel):
    """زیرخدمت (کاشت ژله‌ای، فیشیال VIP...)"""

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='sub_services',
        verbose_name='دسته‌بندی',
    )
    name = models.CharField('نام', max_length=50)
    slug = models.SlugField('اسلاگ')
    type_id = models.CharField(
        'شناسه برای فرانت',
        max_length=50,
        help_text='شناسه برای فرانت',
    )

    class Meta:
        db_table = 'sub_services'
        verbose_name = '📂 زیرخدمت'
        verbose_name_plural = '📂 زیرخدمات'
        unique_together = ['category', 'slug']

    def __str__(self):
        return f'{self.category.name} > {self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class BusinessCategory(BaseModel):
    """نوع کسب‌وکار (سالن، کلینیک، مرکز لیزر...)"""

    name = models.CharField('نام', max_length=50)
    slug = models.SlugField('اسلاگ', unique=True)

    class Meta:
        db_table = 'business_categories'
        verbose_name = '🏪 نوع کسب‌وکار'
        verbose_name_plural = '🏪 انواع کسب‌وکار'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)