"""
سیگنال‌های اپ businesses - نسخه اصلاح شده
استفاده از pre_save برای ذخیره وضعیت قبلی
"""
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Business, Service
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Business)
def store_old_business_status(sender, instance, **kwargs):
    """
    ✅ ذخیره وضعیت قبلی قبل از save
    این signal قبل از save اجرا می‌شود و وضعیت فعلی را ذخیره می‌کند
    """
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
    """
    ✅ اصلاح شده: تشخیص دقیق تغییر وضعیت
    با استفاده از _old_status که در pre_save ذخیره شده
    """
    if created:
        # کسب‌وکار جدید ایجاد شده
        logger.info(f"New business created: {instance.name}")
        return

    # بررسی اینکه آیا وضعیت واقعاً تغییر کرده
    old_status = getattr(instance, '_old_status', None)

    if old_status is None or old_status == instance.status:
        # وضعیت تغییر نکرده
        return

    # وضعیت تغییر کرده - انجام عملیات مربوطه
    logger.info(
        f"Business status changed: {instance.name} "
        f"from {old_status} to {instance.status}"
    )

    if instance.status == Business.Status.APPROVED and old_status != Business.Status.APPROVED:
        # ✅ کسب‌وکار تایید شده
        try:
            # ارسال ایمیل تایید
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

            # ارسال نوتیفیکیشن
            try:
                from apps.notifications.services import NotificationService
                NotificationService.send_business_approved(instance)
            except Exception as e:
                logger.error(f"Failed to send approval notification: {e}")

            logger.info(f"✅ Business approved: {instance.name}")

        except Exception as e:
            logger.error(f"Error sending approval notification: {e}")

    elif instance.status == Business.Status.REJECTED and old_status != Business.Status.REJECTED:
        # ✅ کسب‌وکار رد شده
        try:
            # ارسال ایمیل رد
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

            # ارسال نوتیفیکیشن
            try:
                from apps.notifications.services import NotificationService
                NotificationService.send_business_rejected(instance)
            except Exception as e:
                logger.error(f"Failed to send rejection notification: {e}")

            logger.info(f"❌ Business rejected: {instance.name}")

        except Exception as e:
            logger.error(f"Error sending rejection notification: {e}")


@receiver(post_save, sender=Service)
@receiver(post_delete, sender=Service)
def update_business_services_count(sender, instance, **kwargs):
    """بروزرسانی تعداد خدمات کسب‌وکار"""
    business = instance.business
    if business:
        business.services_count = business.services.filter(is_active=True).count()
        business.save(update_fields=['services_count'])