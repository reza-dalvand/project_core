# shared/national_id/api_ir.py
# جایگزین کامل فایل

"""
API.ir National ID Verifier — Shahkar Lite
مستندات: https://api.ir

اندپوینت: POST /api/sw1/ShahkarLite
فرمت درخواست:
{
    "nationalCode": "0010007700",  ← ۱۰ رقم با صفرهای پیشرو
    "mobile": "09120001111"         ← فرمت ۰۹۱۲۰۰۰۱۱۱۱
}
فرمت پاسخ:
{
    "success": true,
    "data": true,        ← true = تطابق دارد
    "message": "...",
    "code": 0
}
"""
import logging
import requests
from typing import Optional
from .base import AbstractNationalIdVerifier, VerificationResult

logger = logging.getLogger(__name__)


class ApiIrNationalIdVerifier(AbstractNationalIdVerifier):
    """
    استعلام شاهکار از api.ir (نسخه Lite)
    """
    DEFAULT_URL = 'https://s.api.ir/api/sw1/ShahkarLite'

    def __init__(self, api_key: str, api_url: str = None):
        if not api_key or api_key == 'fake-api-key-for-dev':
            raise ValueError(
                'SHAHKAR_API_KEY تنظیم نشده یا مقدار فیک است. '
                'لطفاً کلید واقعی را از پنل api.ir دریافت کنید.'
            )
        self._api_key = api_key
        self._api_url = api_url or self.DEFAULT_URL

    def _normalize_phone(self, phone: str) -> str:
        """
        ✅ FIX: تبدیل شماره به فرمت صحیح شاهکار (09120001111)
        """
        cleaned = str(phone).strip()
        # تبدیل ارقام فارسی به انگلیسی
        cleaned = cleaned.translate(
            str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        )
        cleaned = cleaned.translate(
            str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        )
        # حذف هر چیز غیر عددی به جز +
        cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '+')

        # تبدیل به فرمت 09120001111
        if cleaned.startswith('+98'):
            cleaned = '0' + cleaned[3:]
        elif cleaned.startswith('0098'):
            cleaned = '0' + cleaned[4:]
        elif cleaned.startswith('98') and len(cleaned) == 12:
            cleaned = '0' + cleaned[2:]
        elif not cleaned.startswith('0') and len(cleaned) == 10:
            cleaned = '0' + cleaned

        return cleaned

    def _normalize_national_id(self, national_id: str) -> str:
        """
        ✅ FIX: تبدیل کد ملی به فرمت ۱۰ رقمی با صفرهای پیشرو
        طبق مستندات: "0010007700"
        """
        cleaned = str(national_id).strip()
        cleaned = cleaned.translate(
            str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        )
        cleaned = cleaned.translate(
            str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        )
        cleaned = ''.join(c for c in cleaned if c.isdigit())

        # ✅ FIX: اضافه کردن صفرهای پیشرو برای رسیدن به ۱۰ رقم
        cleaned = cleaned.zfill(10)

        return cleaned

    def verify(
        self,
        national_id: str,
        phone: str,
        full_name: Optional[str] = None,
    ) -> VerificationResult:
        # ✅ FIX: نرمال‌سازی قبل از اعتبارسنجی
        national_id = self._normalize_national_id(national_id)
        phone = self._normalize_phone(phone)

        # اعتبارسنجی کد ملی
        national_id = self.validate_national_id(national_id)

        payload = {
            'nationalCode': national_id,
            'mobile': phone,
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._api_key}',
        }

        try:
            response = requests.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()

                # ✅ FIX: بررسی فیلد success هم
                api_success = data.get('success', False)
                match_result = data.get('data')
                api_message = data.get('message')

                if api_success and match_result is True:
                    return VerificationResult(
                        success=True,
                        verified_name=full_name or '',
                        national_id=national_id,
                    )
                elif match_result is False:
                    return VerificationResult(
                        success=False,
                        error_message=api_message or (
                            'کد ملی با شماره موبایل تطابق ندارد'
                        ),
                        error_code='MISMATCH',
                    )
                else:
                    # ✅ FIX: حالت‌های دیگر (مثلاً خطای نامشخص)
                    return VerificationResult(
                        success=False,
                        error_message=api_message or 'خطا در استعلام',
                        error_code='API_ERROR',
                    )

            elif response.status_code == 401:
                return VerificationResult(
                    success=False,
                    error_message='توکن احراز هویت نامعتبر است',
                    error_code='UNAUTHORIZED',
                )
            elif response.status_code == 429:
                return VerificationResult(
                    success=False,
                    error_message='تعداد درخواست‌ها بیش از حد مجاز است',
                    error_code='RATE_LIMIT',
                )
            else:
                return VerificationResult(
                    success=False,
                    error_message=f'خطا در استعلام (کد: {response.status_code})',
                    error_code='API_ERROR',
                )

        except requests.Timeout:
            return VerificationResult(
                success=False,
                error_message='زمان استعلام به پایان رسید',
                error_code='TIMEOUT',
            )
        except requests.RequestException as e:
            logger.error(f"Shahkar Lite API error: {e}")
            return VerificationResult(
                success=False,
                error_message='خطا در ارتباط با سامانه استعلام',
                error_code='CONNECTION_ERROR',
            )