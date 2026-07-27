"""
سرویس سیستم دعوت از دوستان
"""
from django.db import models, transaction
from django.utils import timezone

from apps.advanced.models import ReferralCode, Referral


class ReferralService:
    """سرویس مدیریت دعوت از دوستان"""

    # پاداش‌ها
    REFERRER_REWARD = 50000  # ۵۰ هزار تومان
    REFERRED_REWARD = 30000  # ۳۰ هزار تومان

    @classmethod
    def get_or_create_code(cls, user):
        """دریافت یا ایجاد کد معرف"""
        code, created = ReferralCode.objects.get_or_create(user=user)
        return code

    @classmethod
    def apply_referral_code(cls, referrer_code, new_user):
        """
        اعمال کد معرف برای کاربر جدید
        """
        # بررسی معتبر بودن کد
        try:
            referral_code = ReferralCode.objects.select_related('user').get(
                code=referrer_code,
                is_active=True,
            )
        except ReferralCode.DoesNotExist:
            return {
                'success': False,
                'message': 'کد معرف نامعتبر است',
            }

        # بررسی: کاربر نمی‌تواند خودش را دعوت کند
        if referral_code.user == new_user:
            return {
                'success': False,
                'message': 'شما نمی‌توانید از کد معرف خودتان استفاده کنید',
            }

        # بررسی تکراری نبودن
        if Referral.objects.filter(referred=new_user).exists():
            return {
                'success': False,
                'message': 'شما قبلاً از کد معرف استفاده کرده‌اید',
            }

        # ایجاد دعوت
        referral = Referral.objects.create(
            referrer=referral_code.user,
            referred=new_user,
            referral_code=referral_code,
            status=Referral.Status.PENDING,
        )

        return {
            'success': True,
            'message': 'کد معرف با موفقیت اعمال شد. با اولین رزرو، پاداش به هر دو طرف تعلق می‌گیرد.',
            'referral_id': referral.id,
        }

    @classmethod
    @transaction.atomic
    def complete_referral(cls, referral, booking):
        """
        تکمیل دعوت (بعد از اولین رزرو موفق)
        """
        if referral.status != Referral.Status.PENDING:
            return False

        referral.status = Referral.Status.COMPLETED
        referral.first_booking = booking
        referral.completed_at = timezone.now()
        referral.save()

        return True

    @classmethod
    @transaction.atomic
    def reward_referral(cls, referral):
        """
        پرداخت پاداش به هر دو طرف
        """
        if referral.status != Referral.Status.COMPLETED:
            return False

        from apps.payments.services.wallet_service import WalletService

        # پاداش دعوت‌کننده
        WalletService.deposit(
            user=referral.referrer,
            amount=cls.REFERRER_REWARD,
            description=f'پاداش دعوت دوست ({referral.referred.phone})',
            reference=f'REFERRAL-{referral.id}-REFERRER',
        )

        # پاداش دعوت‌شده
        WalletService.deposit(
            user=referral.referred,
            amount=cls.REFERRED_REWARD,
            description='پاداش خوش‌آمدگویی (دعوت دوست)',
            reference=f'REFERRAL-{referral.id}-REFERRED',
        )

        # بروزرسانی Referral
        referral.status = Referral.Status.REWARDED
        referral.referrer_reward = cls.REFERRER_REWARD
        referral.referred_reward = cls.REFERRED_REWARD
        referral.rewarded_at = timezone.now()
        referral.save()

        # بروزرسانی آمار کد معرف
        referral.referral_code.total_referrals += 1
        referral.referral_code.total_rewards += cls.REFERRER_REWARD + cls.REFERRED_REWARD
        referral.referral_code.save()

        return True

    @classmethod
    def get_user_stats(cls, user):
        """آمار دعوت‌های کاربر"""
        code = cls.get_or_create_code(user)

        referrals = Referral.objects.filter(referrer=user)

        return {
            'code': code.code,
            'total_referrals': referrals.count(),
            'completed': referrals.filter(status=Referral.Status.COMPLETED).count(),
            'rewarded': referrals.filter(status=Referral.Status.REWARDED).count(),
            'pending': referrals.filter(status=Referral.Status.PENDING).count(),
            'total_rewards': referrals.filter(
                status=Referral.Status.REWARDED
            ).aggregate(total=models.Sum('referrer_reward'))['total'] or 0,
            'referrer_reward': cls.REFERRER_REWARD,
            'referred_reward': cls.REFERRED_REWARD,
        }

    @classmethod
    def get_referrals_list(cls, user, status=None):
        """لیست دعوت‌های کاربر"""
        qs = Referral.objects.filter(referrer=user).select_related(
            'referred', 'first_booking'
        )

        if status:
            qs = qs.filter(status=status)

        return qs.order_by('-created_at')