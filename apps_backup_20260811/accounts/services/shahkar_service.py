"""
Shahkar Service
سرویس تطبیق کد ملی با شماره موبایل از طریق سامانه شاهکار
"""
import logging
import requests
from django.conf import settings
from apps.core.utils import normalize_phone, to_english_digits
from apps.core.exceptions import ShahkarException, ShahkarMismatchException
from apps.core.validators import validate_national_id
import random

logger = logging.getLogger(__name__)


class ShahkarService:
    """
    سرویس استعلام از سامانه شاهکار (ثبت احوال)
    برای تطبیق کد ملی با شماره موبایل
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

        # تبدیل 09... به 989...
        shahkar_phone = phone
        if phone.startswith('0'):
            shahkar_phone = '98' + phone[1:]

        # ─── حالت توسعه: Mock ───
        if settings.DEBUG or not getattr(settings, 'SHAHKAR_API_KEY', ''):
            return cls._mock_verify(national_id, phone, full_name)

        # ─── استعلام واقعی ───
        return cls._real_verify(national_id, shahkar_phone)

    @classmethod
    def _real_verify(cls, national_id: str, phone: str):
        """استعلام واقعی از API شاهکار"""
        try:
            api_url = getattr(settings, 'SHAHKAR_API_URL', '')
            api_key = getattr(settings, 'SHAHKAR_API_KEY', '')

            if not api_url or not api_key:
                raise ShahkarException(message='تنظیمات API شاهکار کامل نیست')

            payload = {
                'national_id': national_id,
                'phone': phone,
            }
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }

            response = requests.post(api_url, json=payload, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get('match'):
                    return {
                        'success': True,
                        'verified_name': data.get('name', ''),
                        'national_id': national_id,
                    }
                else:
                    raise ShahkarMismatchException()

            elif response.status_code == 400:
                raise ShahkarException(
                    message='اطلاعات وارد شده معتبر نیست',
                    details=response.json()
                )
            else:
                raise ShahkarException(
                    message=f'خطا در ارتباط با سامانه شاهکار (کد: {response.status_code})'
                )

        except requests.Timeout:
            raise ShahkarException(message='زمان استعلام به پایان رسید. لطفاً دوباره تلاش کنید')
        except requests.RequestException as e:
            logger.error(f"Shahkar API error: {e}")
            raise ShahkarException(message='خطا در ارتباط با سامانه شاهکار')

    @classmethod
    def _mock_verify(cls, national_id: str, phone: str, full_name: str = None):
        """
        حالت Mock برای توسعه
        کد ملی تست: 0012345679 — همیشه موفق
        """
        # کد تست - همیشه موفق
        if national_id == '0012345679':
            return {
                'success': True,
                'verified_name': 'کاربر آزمایشی زیبانو',
                'national_id': national_id,
            }

        # حالت عادی: ۷۰٪ احتمال موفقیت
        if random.random() < 0.7:
            return {
                'success': True,
                'verified_name': full_name or 'نام تایید شده از سامانه',
                'national_id': national_id,
            }
        else:
            raise ShahkarMismatchException(
                message='کد ملی وارد شده با شماره موبایل ثبت‌نام شده شما تطابق ندارد'
            )