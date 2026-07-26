"""
سیگنال‌های اپ اعلان‌ها
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import CustomUser


@receiver(post_save, sender=CustomUser)
def create_wallet_for_new_user(sender, instance, created, **kwargs):
    """
    با ساخت کاربر جدید، کیف پول هم برایش ساخته شود
    """
    if created:
        # import در داخل تابع برای جلوگیری از circular import
        from apps.payments.models import Wallet
        Wallet.objects.get_or_create(user=instance)