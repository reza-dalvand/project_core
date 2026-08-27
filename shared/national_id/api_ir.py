"""
API.ir National ID Verifier — Shahkar Lite
مستندات: https://api.ir
اندپوینت: POST https://s.api.ir/api/sw1/ShahkarLite

فرمت درخواست:
  Headers: Content-Type: application/json
           Authorization: Bearer <token>
  Body:    {"nationalCode": "0010007700", "mobile": "09120000000"}

فرمت پاسخ:
  {
    "data": true,       ← نتیجه تطابق (true = مطابقت دارد)
    "success": false,
    "code": 0,
    "message": null
  }
"""
import logging
import requests
from typing import Optional
from .base import AbstractNationalIdVerifier, VerificationResult

logger = logging.getLogger(__name__)


class ApiIrNationalIdVerifier(AbstractNationalIdVerifier):
    """
    استعلام شاهکار Lite از api.ir
    """
    DEFAULT_URL = 'https://s.api.ir/api/sw1/ShahkarLite'

    def __init__(self, api_key: str, api_url: str = None):
        if not api_key:
            raise ValueError('SHAHKAR_API_KEY تنظیم نشده است')
        self._api_key = api_key
        self._api_url = api_url or self.DEFAULT_URL

    def verify(
        self,
        national_id: str,
        phone: str,
        full_name: Optional[str] = None,
    ) -> VerificationResult:
        national_id = self.validate_national_id(national_id)
        phone = phone.strip()

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
                match_result = data.get('data')
                message = data.get('message')

                # ✅ data=true یعنی تطابق وجود دارد
                if match_result is True:
                    return VerificationResult(
                        success=True,
                        verified_name=full_name or '',
                        national_id=national_id,
                    )
                # ✅ data=false یعنی تطابق وجود ندارد
                elif match_result is False:
                    return VerificationResult(
                        success=False,
                        error_message='کد ملی با شماره موبایل تطابق ندارد',
                        error_code='MISMATCH',
                    )
                # ✅ data=None یا مقدار دیگر = خطا
                else:
                    return VerificationResult(
                        success=False,
                        error_message=message or 'خطا در استعلام',
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