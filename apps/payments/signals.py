"""
سیگنال‌های اپ مالی
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from apps.payments.models import Transaction, Settlement
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def log_transaction(sender, instance, created, **kwargs):
    """لاگ ایجاد تراکنش"""
    if created:
        logger.info(
            f"Transaction created: {instance.tracking_code} "
            f"({instance.get_type_display()}) - {instance.amount:,} تومان"
        )


@receiver(pre_save, sender=Settlement)
def handle_settlement_status_change(sender, instance, **kwargs):
    """لاگ تغییر وضعیت تسویه"""
    if instance.pk:
        try:
            old = Settlement.objects.get(pk=instance.pk)
            if old.status != instance.status:
                logger.info(
                    f"Settlement {instance.id} status changed: "
                    f"{old.status} -> {instance.status}"
                )
        except Settlement.DoesNotExist:
            pass