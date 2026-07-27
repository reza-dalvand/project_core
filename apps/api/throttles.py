"""
Rate Limiting سفارشی
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle


class OTPSendRateThrottle(AnonRateThrottle):
    """محدودیت ارسال OTP: ۵ درخواست در ۱۰ دقیقه"""
    rate = '5/m'  # ✅ اصلاح شد (۵ درخواست در دقیقه)

    def get_cache_key(self, request, view):
        # محدودیت بر اساس IP + شماره
        ident = request.META.get('REMOTE_ADDR', 'anon')
        phone = request.data.get('phone', '')
        return f'otp_send_{ident}_{phone}'


class OTPVerifyRateThrottle(AnonRateThrottle):
    """محدودیت تایید OTP: ۱۰ تلاش در ۱۰ دقیقه"""
    rate = '10/m' # ✅ اصلاح شد (۱۰ درخواست در دقیقه)


class BurstableUserThrottle(UserRateThrottle):
    """Rate limit انعطاف‌پذیر برای کاربران"""
    rate = '1000/h' # ✅ صحیح


class StrictUserThrottle(UserRateThrottle):
    """Rate limit سخت‌گیرانه"""
    rate = '60/m'   # ✅ اصلاح شد (۶۰ درخواست در دقیقه)


class PaymentThrottle(UserRateThrottle):
    """محدودیت برای تراکنش‌های مالی"""
    rate = '10/m'   # ✅ اصلاح شد (۱۰ درخواست در دقیقه)


class ResendOTPThrottle(SimpleRateThrottle):
    """محدودیت ارسال مجدد OTP - ۶۰ ثانیه"""
    rate = '1/m'    # ✅ اصلاح شد (۱ درخواست در دقیقه)
    scope = 'resend_otp'

    def get_cache_key(self, request, view):
        phone = request.data.get('phone', '')
        return f'resend_otp_{phone}'