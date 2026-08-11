"""
API.ir National ID Verifier برای محیط پروداکشن
استعلام از سامانه شاهکار / ثبت احوال
"""
import logging
import requests
from typing import Optional

from .base import AbstractNationalIdVerifier, VerificationResult

logger = logging.getLogger(__name__)


class ApiIrNationalIdVerifier(AbstractNationalIdVerifier):
    """
    استعلام واقعی کد ملی از API
    """

    def __init__(self, api_url: str, api_key: str):
        if not api_url or not api_key:
            raise ValueError('تنظیمات API استعلام کد ملی کامل نیست')
        self._api_url = api_url
        self._api_key = api_key

    def verify(
        self,
        national_id: str,
        phone: str,
        full_name: Optional[str] = None,
    ) -> VerificationResult:
        national_id = self.validate_national_id(national_id)
        shahkar_phone = self.normalize_phone_for_shahkar(phone)

        try:
            payload = {
                'national_id': national_id,
                'phone': shahkar_phone,
            }
            headers = {
                'Authorization': f'Bearer {self._api_key}',
                'Content-Type': 'application/json',
            }

            response = requests.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('match'):
                    return VerificationResult(
                        success=True,
                        verified_name=data.get('name', ''),
                        national_id=national_id,
                    )
                return VerificationResult(
                    success=False,
                    error_message='کد ملی با شماره موبایل تطابق ندارد',
                    error_code='MISMATCH',
                )

            elif response.status_code == 400:
                return VerificationResult(
                    success=False,
                    error_message='اطلاعات وارد شده معتبر نیست',
                    error_code='INVALID_INPUT',
                )

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
            logger.error(f"National ID API error: {e}")
            return VerificationResult(
                success=False,
                error_message='خطا در ارتباط با سامانه استعلام',
                error_code='CONNECTION_ERROR',
            )