"""
سرویس سیستم دعوت از دوستان
✅ بهینه‌شده: Conditional Aggregation برای آمار
"""
from django.db import models, transaction
from django.db.models import Count, Case, When, Value, IntegerField, Sum, Q
from django.utils import timezone
from apps.advanced.models import ReferralCode, Referral


class ReferralService:
    """سرویس مدیریت دعوت از دوستان"""

    REFERRER_REWARD = 50000
    REFERRED_REWARD = 30000

    @classmethod
    def get_or_create_code(cls, user):
        """دریافت یا ایجاد کد معرف"""
        code, created = ReferralCode.objects.get_or_create(user=user)
        return code

    @classmethod
    def apply_referral_code(cls, referrer_code, new_user):
        """اعمال کد معرف برای کاربر جدید"""
        try:
            referral_code = ReferralCode.objects.select_related('user').get(
                code=referrer_code,
                is_active=True,
            )
        except ReferralCode.DoesNotExist:
            return {'success': False, 'message': 'کد معرف نامعتبر است'}

        if referral_code.user == new_user:
            return {'success': False, 'message': 'شما نمی‌توانید از کد معرف خودتان استفاده کنید'}

        if Referral.objects.filter(referred=new_user).exists():
            return {'success': False, 'message': 'شما قبلاً از کد معرف استفاده کرده‌اید'}

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
        """تکمیل دعوت (بعد از اولین رزرو موفق)"""
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
        """پرداخت پاداش به هر دو طرف"""
        if referral.status != Referral.Status.COMPLETED:
            return False

        from apps.payments.services.wallet_service import WalletService

        WalletService.deposit(
            user=referral.referrer,
            amount=cls.REFERRER_REWARD,
            description=f'پاداش دعوت دوست ({referral.referred.phone})',
            reference=f'REFERRAL-{referral.id}-REFERRER',
        )

        WalletService.deposit(
            user=referral.referred,
            amount=cls.REFERRED_REWARD,
            description='پاداش خوش‌آمدگویی (دعوت دوست)',
            reference=f'REFERRAL-{referral.id}-REFERRED',
        )

        referral.status = Referral.Status.REWARDED
        referral.referrer_reward = cls.REFERRER_REWARD
        referral.referred_reward = cls.REFERRED_REWARD
        referral.rewarded_at = timezone.now()
        referral.save()

        # ✅ بهینه: استفاده از F() برای جلوگیری از race condition
        ReferralCode.objects.filter(id=referral.referral_code_id).update(
            total_referrals=models.F('total_referrals') + 1,
            total_rewards=models.F('total_rewards') + cls.REFERRER_REWARD + cls.REFERRED_REWARD,
        )

        return True

    @classmethod
    def get_user_stats(cls, user):
        """
        ✅ بهینه: همه آمار در یک کوئری با Conditional Aggregation
        به جای ۵ کوئری جداگانه
        """
        code = cls.get_or_create_code(user)

        stats = Referral.objects.filter(referrer=user).aggregate(
            total=Count('id'),
            completed=Count(
                Case(When(status=Referral.Status.COMPLETED, then=1), output_field=IntegerField())
            ),
            rewarded=Count(
                Case(When(status=Referral.Status.REWARDED, then=1), output_field=IntegerField())
            ),
            pending=Count(
                Case(When(status=Referral.Status.PENDING, then=1), output_field=IntegerField())
            ),
            total_rewards=Sum(
                Case(
                    When(status=Referral.Status.REWARDED, then='referrer_reward'),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
        )

        return {
            'code': code.code,
            'total_referrals': stats['total'] or 0,
            'completed': stats['completed'] or 0,
            'rewarded': stats['rewarded'] or 0,
            'pending': stats['pending'] or 0,
            'total_rewards': stats['total_rewards'] or 0,
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