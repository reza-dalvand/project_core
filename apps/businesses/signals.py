"""
سیگنال‌های اپ businesses
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Business
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Business)
def store_old_business_status(sender, instance, **kwargs):
    """ذخیره وضعیت قبلی قبل از save"""
    if instance.pk:
        try:
            old_instance = Business.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Business.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Business)
def business_status_changed(sender, instance, created, **kwargs):
    """تشخیص تغییر وضعیت کسب‌وکار و ارسال اعلان"""
    if created:
        logger.info(f"New business created: {instance.name}")
        return

    old_status = getattr(instance, '_old_status', None)
    if old_status is None or old_status == instance.status:
        return

    logger.info(
        f"Business status changed: {instance.name} "
        f"from {old_status} to {instance.status}"
    )

    if instance.status == Business.Status.APPROVED and old_status != Business.Status.APPROVED:
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_business_approved(instance)
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")

    elif instance.status == Business.Status.REJECTED and old_status != Business.Status.REJECTED:
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_business_rejected(instance)
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {e}")