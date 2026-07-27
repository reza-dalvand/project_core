"""
سیگنال‌های اپ businesses
✅ بهینه‌شده: استفاده از update() به جای save()
"""
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count
from .models import Business, Service
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
    """تشخیص دقیق تغییر وضعیت"""
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
            if getattr(instance.owner, 'email', ''):
                send_mail(
                    subject=f'تایید کسب‌وکار {instance.name}',
                    message=(
                        f'تبریک! کسب‌وکار "{instance.name}" شما در زیبانو تایید شد.\n'
                        f'اکنون می‌توانید خدمات خود را ثبت و نوبت‌دهی را شروع کنید.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.owner.email],
                    fail_silently=True,
                )
            try:
                from apps.notifications.services import NotificationService
                NotificationService.send_business_approved(instance)
            except Exception as e:
                logger.error(f"Failed to send approval notification: {e}")
        except Exception as e:
            logger.error(f"Error sending approval notification: {e}")

    elif instance.status == Business.Status.REJECTED and old_status != Business.Status.REJECTED:
        try:
            if getattr(instance.owner, 'email', ''):
                send_mail(
                    subject=f'رد کسب‌وکار {instance.name}',
                    message=(
                        f'متاسفانه کسب‌وکار "{instance.name}" شما در زیبانو تایید نشد.\n'
                        f'دلیل رد: {instance.rejection_reason}\n'
                        f'لطفاً اطلاعات را اصلاح و مجدداً ارسال کنید.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.owner.email],
                    fail_silently=True,
                )
            try:
                from apps.notifications.services import NotificationService
                NotificationService.send_business_rejected(instance)
            except Exception as e:
                logger.error(f"Failed to send rejection notification: {e}")
        except Exception as e:
            logger.error(f"Error sending rejection notification: {e}")


@receiver(post_save, sender=Service)
@receiver(post_delete, sender=Service)
def update_business_services_count(sender, instance, **kwargs):
    """
    ✅ بهینه: استفاده از update() به جای save()
    یک کوئری به جای دو کوئری
    """
    business = instance.business
    if business:
        count = Service.objects.filter(
            business=business,
            is_active=True
        ).count()

        # ✅ update() یک کوئری است
        Business.objects.filter(id=business.id).update(
            services_count=count
        )