"""
سیگنال‌های اپ احراز هویت
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def user_post_save(sender, instance, created, **kwargs):
    """
    پس از ذخیره کاربر:
    - اگر business_owner شد و national_id تایید شده، بررسی‌های اضافی
    """
    if created:
        # کارهای اولیه بعد از ثبت‌نام
        pass

    # اگر نقش کاربر تغییر کرد
    if instance.role == CustomUser.Role.BUSINESS_OWNER:
        # چک کردن اینکه national_id تایید شده
        if not instance.national_id_verified:
            # صاحب کسب‌وکار باید کد ملی تایید شده داشته باشد
            pass