"""
سیگنال‌های اپ احراز هویت
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User  # ✅


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """پس از ذخیره کاربر جدید"""
    if created:
        # UserReferral برای کاربر جدید
        from .models import UserReferral
        import secrets
        UserReferral.objects.get_or_create(
            user=instance,
            defaults={
                'referral_code': f'ZIBANO-{secrets.token_hex(4).upper()}',
                'is_active': False,
            }
        )