"""
Shahkar Service
سرویس تطبیق کد ملی با شماره موبایل از طریق شاهکار Lite (api.ir)
"""
import logging
import random
from django.conf import settings
from apps.core.utils import normalize_phone, to_english_digits
from apps.core.exceptions import ShahkarException, ShahkarMismatchException
from apps.core.validators import validate_national_id

logger = logging.getLogger(__name__)


class ShahkarService:
    """
    سرویس استعلام شاهکار (ثبت احوال) — نسخه Shahkar Lite
    """

    @classmethod
    def verify(cls, national_id: str, phone: str, full_name: str = None):
        """
        استعلام تطبیق کد ملی با شماره موبایل
        """
        # نرمال‌سازی ورودی‌ها
        national_id = to_english_digits(str(national_id)).strip()
        phone = normalize_phone(phone)

        # اعتبارسنجی
        try:
            national_id = validate_national_id(national_id)
        except Exception as e:
            raise ShahkarException(message=str(e))

        # ─── حالت توسعه: Mock ───
        if settings.DEBUG or not getattr(settings, 'SHAHKAR_API_KEY', ''):
            return cls._mock_verify(national_id, phone, full_name)

        # ─── استعلام واقعی ───
        return cls._real_verify(national_id, phone, full_name)

    @classmethod
    def _real_verify(cls, national_id: str, phone: str, full_name: str = None):
        """استعلام واقعی از Shahkar Lite (api.ir)"""
        from shared.national_id import get_national_id_verifier

        try:
            verifier = get_national_id_verifier()
            result = verifier.verify(national_id, phone, full_name)

            if result.success:
                return {
                    'success': True,
                    'verified_name': result.verified_name or full_name or '',
                    'national_id': result.national_id,
                }

            if result.error_code == 'MISMATCH':
                raise ShahkarMismatchException(
                    message=result.error_message
                )

            raise ShahkarException(
                message=result.error_message,
                code=result.error_code,
            )

        except (ShahkarException, ShahkarMismatchException):
            raise
        except Exception as e:
            logger.error(f"Shahkar verify error: {e}")
            raise ShahkarException(message='خطا در استعلام کد ملی')

    @classmethod
    def _mock_verify(cls, national_id: str, phone: str, full_name: str = None):
        """
        حالت Mock برای توسعه
        کد ملی تست: 0012345679 — همیشه موفق
        """
        if national_id == '0012345679':
            return {
                'success': True,
                'verified_name': 'کاربر آزمایشی بیو کلاب',
                'national_id': national_id,
            }

        if random.random() < 0.7:
            return {
                'success': True,
                'verified_name': full_name or 'نام تایید شده از سامانه',
                'national_id': national_id,
            }

        raise ShahkarMismatchException(
            message='کد ملی وارد شده با شماره موبایل ثبت‌نام شده شما تطابق ندارد'
        )