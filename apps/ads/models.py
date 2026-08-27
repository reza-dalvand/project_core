"""
آگهی‌ها (مدلینگ + اجاره لاین)
+ فیلد location برای فیلتر فاصله (فاز ۳)
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from apps.core.models import BaseModel


class ModelRequest(BaseModel):
    """درخواست مدل"""
    class CostType(models.TextChoices):
        PAID = 'paid', 'با هزینه'
        MATERIAL_COST = 'material_cost', 'با هزینه مواد'
        FREE = 'free', 'رایگان'

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='model_requests',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        verbose_name='خدمت',
    )
    title = models.CharField('عنوان', max_length=100)
    description = models.TextField('توضیحات', max_length=500)
    service_image = models.ImageField(
        'تصویر خدمت',
        upload_to='ads/model_requests/',
    )
    cost_type = models.CharField(
        'نوع هزینه',
        max_length=20,
        choices=CostType.choices,
        default=CostType.MATERIAL_COST,
    )
    discount = models.IntegerField('درصد تخفیف', default=0)
    is_urgent = models.BooleanField('فوری', default=False)
    contact_phone = models.CharField('شماره تماس', max_length=11)

    # ═══ تاریخ جلالی ═══
    created_jalali = models.CharField('تاریخ ایجاد جلالی', max_length=10)
    expires_jalali = models.CharField('تاریخ انقضای جلالی', max_length=10)

    # ═══ 🆕 فاز ۳: موقعیت جغرافیایی ═══
    location = gis_models.PointField(
        'موقعیت جغرافیایی',
        null=True,
        blank=True,
        geography=True,
    )

    class Meta:
        db_table = 'model_requests'
        verbose_name = '👤 درخواست مدل'
        verbose_name_plural = '👤 درخواست‌های مدل'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.business.name} - {self.title}'

    def save(self, *args, **kwargs):
        # کپی location از کسب‌وکار
        if not self.location and self.business_id:
            self.location = self.business.location
        super().save(*args, **kwargs)


class LineRental(BaseModel):
    """آگهی اجاره لاین"""
    class CollabType(models.TextChoices):
        PERCENT = 'percent', 'درصدی'
        FIXED = 'fixed', 'اجاره ثابت'
        HOURLY = 'hourly', 'ساعتی'

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='line_rentals',
        verbose_name='کسب‌وکار',
    )
    title = models.CharField('عنوان آگهی', max_length=100)
    description = models.TextField('توضیحات', max_length=500)
    line_image = models.ImageField(
        'تصویر لاین',
        upload_to='ads/line_rentals/',
    )
    service_category = models.ForeignKey(
        'categories.ServiceCategory',
        on_delete=models.PROTECT,
        verbose_name='دسته‌بندی خدمات',
    )
    sub_service = models.ForeignKey(
        'categories.SubService',
        on_delete=models.PROTECT,
        verbose_name='زیرخدمت',
    )

    # ═══ نوع همکاری ═══
    collab_type = models.CharField(
        'نوع همکاری',
        max_length=20,
        choices=CollabType.choices,
    )
    percent_salon = models.IntegerField('سهم سالن (%)', null=True, blank=True)
    percent_partner = models.IntegerField('سهم همکار (%)', null=True, blank=True)
    fixed_amount = models.BigIntegerField('مبلغ اجاره ثابت', null=True, blank=True)
    fixed_deposit = models.BigIntegerField('رهن / ودیعه', null=True, blank=True)
    hourly_rate = models.BigIntegerField('نرخ ساعتی', null=True, blank=True)
    contact_phone = models.CharField('شماره تماس', max_length=11)

    # ═══ تاریخ جلالی ═══
    created_jalali = models.CharField('تاریخ ایجاد جلالی', max_length=10)
    expires_jalali = models.CharField('تاریخ انقضای جلالی', max_length=10)

    # ═══ 🆕 فاز ۳: موقعیت جغرافیایی ═══
    location = gis_models.PointField(
        'موقعیت جغرافیایی',
        null=True,
        blank=True,
        geography=True,
    )

    class Meta:
        db_table = 'line_rentals'
        verbose_name = '🏬 آگهی اجاره لاین'
        verbose_name_plural = '🏬 آگهی‌های اجاره لاین'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.business.name} - {self.title}'

    def clean(self):
        if self.collab_type == self.CollabType.PERCENT:
            if self.percent_salon and self.percent_partner:
                if self.percent_salon + self.percent_partner != 100:
                    raise ValidationError('مجموع درصدها باید ۱۰۰٪ باشد')

    def save(self, *args, **kwargs):
        # کپی location از کسب‌وکار
        if not self.location and self.business_id:
            self.location = self.business.location
        super().save(*args, **kwargs)