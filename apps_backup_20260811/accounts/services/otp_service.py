"""
OTP Service با پشتیبانی از کاوه‌نگار
"""
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import OTP
from apps.core.utils import generate_otp, normalize_phone
from apps.core.exceptions import (
    OTPExpiredException,
    OTPInvalidException,
    OTPTooManyAttemptsException,
    OTPRateLimitException,
)

logger = logging.getLogger(__name__)


class OTPService:
    """
    سرویس مدیریت کدهای تایید (OTP)
    """

    OTP_LENGTH = 5
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 5
    RESEND_COOLDOWN_SECONDS = 60

    @classmethod
    def send_otp(cls, phone: str, purpose: str = OTP.Purpose.LOGIN, user=None):
        """
        ارسال کد تایید به شماره موبایل
        """
        phone = normalize_phone(phone)

        # Rate limiting: بررسی ارسال‌های اخیر
        recent_otp = OTP.objects.filter(
            phone=phone,
            purpose=purpose,
            created_at__gte=timezone.now() - timedelta(seconds=cls.RESEND_COOLDOWN_SECONDS)
        ).first()

        if recent_otp:
            remaining = cls.RESEND_COOLDOWN_SECONDS - int(
                (timezone.now() - recent_otp.created_at).total_seconds()
            )
            raise OTPRateLimitException(
                message=f'لطفاً {remaining} ثانیه صبر کنید و دوباره تلاش کنید',
                details={'remaining_seconds': remaining}
            )

        # غیرفعال کردن OTP های قبلی
        OTP.objects.filter(phone=phone, purpose=purpose, is_used=False).update(is_used=True)

        # تولید OTP جدید
        code = generate_otp(cls.OTP_LENGTH)
        expires_at = timezone.now() + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)

        otp = OTP.objects.create(
            phone=phone,
            user=user,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
            max_attempts=cls.MAX_ATTEMPTS,
        )

        # ارسال پیامک
        cls._send_sms(phone, code, purpose)

        logger.info(f"OTP sent to {phone} for {purpose}")
        return otp

    @classmethod
    def verify_otp(cls, phone: str, code: str, purpose: str = OTP.Purpose.LOGIN):
        """
        بررسی صحت کد تایید
        """
        phone = normalize_phone(phone)

        # پیدا کردن آخرین OTP معتبر
        otp = OTP.objects.filter(
            phone=phone,
            purpose=purpose,
            is_used=False,
        ).order_by('-created_at').first()

        if not otp:
            raise OTPInvalidException('کد تاییدی یافت نشد. لطفاً ابتدا درخواست کد دهید')

        # بررسی انقضا
        if otp.is_expired:
            raise OTPExpiredException()

        # بررسی تعداد تلاش
        if otp.attempts >= otp.max_attempts:
            raise OTPTooManyAttemptsException()

        # بررسی صحت کد
        if not otp.verify(code):
            remaining_attempts = otp.max_attempts - otp.attempts
            raise OTPInvalidException(
                message=f'کد وارد شده صحیح نیست. {remaining_attempts} تلاش باقی مانده',
                details={'remaining_attempts': remaining_attempts}
            )

        return otp

    @classmethod
    def _send_sms(cls, phone: str, code: str, purpose: str):
        """ارسال پیامک از طریق کاوه‌نگار"""
        try:
            from kavenegar import KavenegarAPI, APIException, HTTPException

            api_key = getattr(settings, 'KAVENEGAR_API_KEY', '')
            if not api_key:
                logger.warning(f"[DEV MODE] OTP for {phone}: {code}")
                return

            api = KavenegarAPI(api_key)

            # انتخاب template بر اساس purpose
            template_map = {
                OTP.Purpose.LOGIN: 'zibano-login',
                OTP.Purpose.CHANGE_PHONE: 'zibano-change-phone',
                OTP.Purpose.VERIFY_NATIONAL_ID: 'zibano-verify-id',
            }
            template_name = template_map.get(purpose, 'zibano-login')

            params = {
                'receptor': phone,
                'template': template_name,
                'token': code,
            }

            response = api.VerifyLookup(params)
            message_id = response['entries']['messageid']
            logger.info(f"SMS sent to {phone}, message_id: {message_id}")

            # لاگ در SMSLog
            try:
                from apps.notifications.models import SMSLog
                SMSLog.objects.create(
                    phone=phone,
                    message=f'کد تایید: {code}',
                    status=SMSLog.Status.SENT,
                    provider_message_id=str(message_id),
                    cost=response['entries'].get('cost', 0),
                )
            except Exception as e:
                logger.warning(f"Failed to log SMS: {e}")

        except ImportError:
            logger.warning(f"[DEV MODE] OTP for {phone}: {code}")
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {e}")
            # در حالت development، خطا را ignore کن
            if not settings.DEBUG:
                raise