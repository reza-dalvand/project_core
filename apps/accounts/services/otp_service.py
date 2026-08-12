"""
OTP Service — هماهنگ با مدل OtpCode و shared/sms
"""
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import OtpCode
from apps.core.utils import generate_otp, normalize_phone
from apps.core.exceptions import (
    OTPExpiredException,
    OTPInvalidException,
    OTPRateLimitException,
)

logger = logging.getLogger(__name__)


class OTPService:
    """سرویس مدیریت کدهای تایید (OTP)"""

    OTP_LENGTH = 5
    OTP_EXPIRY_MINUTES = 5
    RESEND_COOLDOWN_SECONDS = 60

    @classmethod
    def send_otp(cls, phone: str, purpose: str = OtpCode.Purpose.LOGIN, user=None):
        """ارسال کد تایید به شماره موبایل"""
        phone = normalize_phone(phone)

        # Rate limiting: جلوگیری از ارسال مجدد زیر ۶۰ ثانیه
        recent_otp = OtpCode.objects.filter(
            phone=phone,
            purpose=purpose,
            created_at__gte=timezone.now() - timedelta(seconds=cls.RESEND_COOLDOWN_SECONDS),
        ).first()
        if recent_otp:
            remaining = cls.RESEND_COOLDOWN_SECONDS - int(
                (timezone.now() - recent_otp.created_at).total_seconds()
            )
            raise OTPRateLimitException(
                message=f'لطفاً {remaining} ثانیه صبر کنید و دوباره تلاش کنید',
                details={'remaining_seconds': remaining},
            )

        # غیرفعال کردن OTP های قبلی استفاده‌نشده
        OtpCode.objects.filter(phone=phone, purpose=purpose, is_used=False).update(is_used=True)

        # تولید OTP جدید
        code = generate_otp(cls.OTP_LENGTH)
        otp = OtpCode.objects.create(
            phone=phone,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=cls.OTP_EXPIRY_MINUTES),
        )

        # ارسال پیامک (در dev از MockSmsProvider استفاده می‌شه)
        cls._send_sms(phone, code)
        logger.info(f"OTP sent to {phone} for {purpose}")
        return otp

    @classmethod
    def verify_otp(cls, phone: str, code: str, purpose: str = OtpCode.Purpose.LOGIN):
        """بررسی صحت کد تایید"""
        phone = normalize_phone(phone)

        otp = OtpCode.objects.filter(
            phone=phone,
            purpose=purpose,
            is_used=False,
        ).order_by('-created_at').first()

        if not otp:
            raise OTPInvalidException('کد تاییدی یافت نشد. لطفاً ابتدا درخواست کد دهید')

        if otp.is_expired:
            raise OTPExpiredException()

        if not otp.verify(code):
            raise OTPInvalidException('کد وارد شده صحیح نیست')

        return otp

    @classmethod
    def _send_sms(cls, phone: str, code: str):
        """ارسال پیامک از طریق provider (shared/sms)"""
        try:
            from shared.sms import get_sms_provider
            provider = get_sms_provider()
            provider.send_otp(phone, code)
        except Exception as e:
            logger.error(f"Failed to send OTP SMS to {phone}: {e}")
            # در پروداکشن خطا را بالا بده، در dev فقط لاگ کن
            if not settings.DEBUG:
                raise