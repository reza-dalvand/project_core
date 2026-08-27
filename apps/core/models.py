"""
Base Model برای تمام مدل‌های بیو کلاب
"""
from django.db import models


class BaseModel(models.Model):
    """بیس‌مدل برای همه مدل‌ها"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class AppConfig(models.Model):
    """
    تنظیمات اپلیکیشن — فقط یک رکورد
    از طریق ادمین قابل ویرایش است.
    فرانت از دو اندپوینت می‌خواند:
      GET /api/v1/config/app-version/
      GET /api/v1/config/maintenance-status/
    """

    # ─── نسخه اپلیکیشن ───
    latest_version = models.CharField(
        'آخرین نسخه',
        max_length=20,
        default='1.0.0',
    )
    min_required_version = models.CharField(
        'حداقل نسخه مورد نیاز',
        max_length=20,
        default='1.0.0',
    )
    is_force_update = models.BooleanField(
        'آپدیت اجباری',
        default=False,
    )
    update_title = models.CharField(
        'عنوان آپدیت',
        max_length=200,
        default='نسخه جدید بیو کلاب منتشر شد!',
    )
    update_message = models.TextField(
        'پیام آپدیت',
        default='برای تجربه بهتر، لطفاً به آخرین نسخه به‌روزرسانی کنید.',
    )
    changelog = models.JSONField(
        'تغییرات نسخه',
        default=list,
        blank=True,
        help_text='لیست تغییرات: [{"icon": "✨", "text": "بهبود عملکرد"}]',
    )
    store_url = models.URLField(
        'لینک آپدیت',
        default='https://beauclub.ir',
        blank=True,
    )
    store_name = models.CharField(
        'نام فروشگاه',
        max_length=100,
        default='بیو کلاب وب',
        blank=True,
    )

    # ─── حالت تعمیرات ───
    is_maintenance = models.BooleanField(
        'حالت تعمیرات فعال',
        default=False,
    )
    maintenance_title = models.CharField(
        'عنوان تعمیرات',
        max_length=200,
        default='در حال بروزرسانی هستیم 🔧',
    )
    maintenance_message = models.TextField(
        'پیام تعمیرات',
        default='تیم فنی بیو کلاب در حال انجام بهبودهای لازم است. لطفاً دقایقی دیگر مراجعه فرمایید.',
    )
    maintenance_estimated_end = models.CharField(
        'زمان تقریبی پایان',
        max_length=100,
        blank=True,
        default='',
    )
    maintenance_reason = models.TextField(
        'دلیل تعمیرات',
        blank=True,
        default='',
    )
    support_phone = models.CharField(
        'شماره پشتیبانی',
        max_length=20,
        blank=True,
        default='',
    )

    class Meta:
        db_table = 'app_config'
        verbose_name = '⚙️ تنظیمات اپلیکیشن'
        verbose_name_plural = '⚙️ تنظیمات اپلیکیشن'

    def __str__(self):
        return f'تنظیمات اپ — نسخه {self.latest_version}'

    def save(self, *args, **kwargs):
        # فقط یک رکورد مجاز است
        if not self.pk and AppConfig.objects.exists():
            existing = AppConfig.objects.first()
            existing.delete()
        super().save(*args, **kwargs)