"""
سیگنال‌های اپ احراز هویت
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def user_post_save(sender, instance, created, **kwargs):
    """پس از ذخیره کاربر، کیف پول هم بساز"""
    if created:
        # import در داخل تابع برای جلوگیری از circular import
        from apps.payments.models import Wallet
        Wallet.objects.get_or_create(user=instance)