"""
سیگنال‌های اپ مالی
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Transaction, Wallet


@receiver(post_save, sender=Transaction)
def handle_transaction_status_change(sender, instance, created, **kwargs):
    """
    وقتی وضعیت تراکنش تغییر کرد:
    - اگر SUCCESS شد: تاریخ paid_at را ست کن
    """
    if not created and instance.status == 'success' and not instance.paid_at:
        instance.paid_at = timezone.now()
        instance.save(update_fields=['paid_at'])


@receiver(post_save, sender=Wallet)
def ensure_wallet_on_user_create(sender, instance, created, **kwargs):
    """
    اگر کیف پول جدیدی ساخته شد، لاگ بگیر
    (در سیگنال accounts، wallet به صورت خودکار ساخته می‌شود)
    """
    if created:
        print(f'✅ کیف پول جدید برای {instance.user.phone} ایجاد شد')