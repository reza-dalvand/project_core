"""
سیگنال‌های ویژگی‌های پیشرفته - نسخه بهینه شده
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import CustomUser
from apps.bookings.models import Appointment


@receiver(post_save, sender=CustomUser)
def create_referral_code_for_user(sender, instance, created, **kwargs):
    """ایجاد کد معرف برای کاربر جدید"""
    if created:
        from apps.advanced.models import ReferralCode
        ReferralCode.objects.get_or_create(user=instance)


@receiver(post_save, sender=Appointment)
def check_referral_completion(sender, instance, created, update_fields=None, **kwargs):
    """
    ✅ بهینه شده: بررسی تکمیل دعوت بعد از اولین رزرو موفق

    تغییرات:
    - استفاده از update_fields برای جلوگیری از اجرای غیرضروری
    - فقط وقتی status تغییر کرده اجرا می‌شود
    - فیلتر کردن سریع‌تر
    """
    # ✅ اگر نوبت جدید ایجاد شده، نیازی به بررسی نیست
    if created:
        return

    # ✅ اگر update_fields مشخص شده و status در آن نیست، اجرا نکن
    if update_fields and 'status' not in update_fields:
        return

    # ✅ فقط برای وضعیت‌های خاص
    if instance.status not in [Appointment.Status.CONFIRMED, Appointment.Status.DONE]:
        return

    # ✅ بررسی وجود دعوت برای این کاربر
    from apps.advanced.models import Referral

    try:
        referral = Referral.objects.select_related(
            'referrer', 'referral_code'
        ).get(
            referred=instance.customer,
            status=Referral.Status.PENDING,
        )

        # تکمیل دعوت
        from apps.advanced.services.referral_service import ReferralService

        if ReferralService.complete_referral(referral, instance):
            # پرداخت پاداش
            ReferralService.reward_referral(referral)

    except Referral.DoesNotExist:
        # این کاربر دعوت نشده
        pass
    except Exception as e:
        # لاگ خطا بدون متوقف کردن فرآیند
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in referral completion signal: {e}")