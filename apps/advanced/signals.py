"""
سیگنال‌های ویژگی‌های پیشرفته
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
def check_referral_completion(sender, instance, created, **kwargs):
    """بررسی تکمیل دعوت بعد از اولین رزرو موفق"""
    if created:
        return

    # فقط نوبت‌های تایید شده یا انجام شده
    if instance.status not in [Appointment.Status.CONFIRMED, Appointment.Status.DONE]:
        return

    from apps.advanced.models import Referral

    # بررسی اینکه آیا این کاربر دعوت شده است
    try:
        referral = Referral.objects.select_related('referrer', 'referral_code').get(
            referred=instance.customer,
            status=Referral.Status.PENDING,
        )

        # تکمیل دعوت
        from apps.advanced.services.referral_service import ReferralService
        if ReferralService.complete_referral(referral, instance):
            # پرداخت پاداش
            ReferralService.reward_referral(referral)

    except Referral.DoesNotExist:
        pass