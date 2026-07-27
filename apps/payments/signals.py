"""
سیگنال‌های اپ مالی
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.payments.models import Transaction, Wallet, Settlement


@receiver(post_save, sender=Transaction)
def handle_transaction_status_change(sender, instance, created, **kwargs):
    """
    وقتی وضعیت تراکنش تغییر کرد:
    - اگر SUCCESS شد: تاریخ paid_at را ست کن
    """
    if not created and instance.status == Transaction.Status.SUCCESS and not instance.paid_at:
        instance.paid_at = timezone.now()
        instance.save(update_fields=['paid_at'])


@receiver(post_save, sender=Wallet)
def log_wallet_change(sender, instance, created, **kwargs):
    """لاگ تغییرات کیف پول"""
    if created:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Wallet created for user {instance.user.phone}")


@receiver(pre_save, sender=Settlement)
def handle_settlement_status_change(sender, instance, **kwargs):
    """
    وقتی وضعیت تسویه تغییر کرد
    """
    if instance.pk:
        try:
            old = Settlement.objects.get(pk=instance.pk)
            if old.status != instance.status:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Settlement {instance.id} status changed: "
                    f"{old.status} -> {instance.status}"
                )
        except Settlement.DoesNotExist:
            pass