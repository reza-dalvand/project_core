"""
مدیریت تبلیغات (برای آینده - فقط مدل)
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
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


class AdBanner(BaseModel):
    """
    بنر تبلیغاتی اسلایدر صفحه اصلی
    شامل عکس، عنوان، توضیحات و لینک به کسب‌وکار یا URL دلخواه
    """
    title = models.CharField('عنوان', max_length=100)
    description = models.CharField(
        'توضیحات (زیرعنوان)', 
        max_length=255, 
        blank=True, 
        default=''
    )
    image = models.ImageField('تصویر بنر', upload_to='promotions/slides/%Y/%m/')   
     
    # ارتباط با کسب‌وکار (برای لینک شدن به پروفایل)
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ad_banners',
        verbose_name='کسب‌وکار مقصد',
        help_text='در صورت انتخاب، کلیک روی بنر کاربر را به پروفایل این کسب‌وکار می‌برد.'
    )
    custom_url = models.URLField(
        'لینک دلخواه',
        blank=True,
        default='',
        help_text='اگر کسب‌وکار انتخاب نشود، می‌توانید لینک دلخواه (مثل لینک ثبت‌نام) وارد کنید.'
    )
    
    badge = models.CharField(
        'متن بج (اختیاری)',
        max_length=50,
        blank=True,
        default='',
        help_text='مثال: ۲۰٪ تخفیف، جدید، پیشنهادات ویژه'
    )
    
    order = models.IntegerField('ترتیب نمایش', default=0, db_index=True)
    
    starts_at = models.DateTimeField('تاریخ شروع', null=True, blank=True)
    expires_at = models.DateTimeField('تاریخ انقضا', null=True, blank=True)

    class Meta:
        db_table = 'ad_banners'
        verbose_name = '🖼️ بنر اسلایدر'
        verbose_name_plural = '🖼️ بنرهای اسلایدر'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        if not self.business and not self.custom_url:
            raise ValidationError('باید إما یک کسب‌وکار مقصد انتخاب کنید یا لینک دلخواه وارد کنید.')
        
    @property
    def is_live(self):
        """بررسی اینکه آیا بنر در حال حاضر باید نمایش داده شود یا خیر"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        return True