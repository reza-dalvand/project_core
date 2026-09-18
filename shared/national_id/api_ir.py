# shared/national_id/api_ir.py
import logging
import requests
from typing import Optional
from .base import AbstractNationalIdVerifier, VerificationResult

logger = logging.getLogger(__name__)

class ApiIrNationalIdVerifier(AbstractNationalIdVerifier):
    DEFAULT_URL = 'https://s.api.ir/api/sw1/ShahkarLite'

    def __init__(self, api_key: str, api_url: str = None):
        self._api_key = api_key.strip().strip('"').strip("'")
        self._api_url = api_url or self.DEFAULT_URL

    def verify(
        self, 
        national_id: str, 
        phone: str, 
        full_name: Optional[str] = None
    ) -> VerificationResult:
        payload = {
            "nationalCode": national_id,
            "mobile": phone
        }

        auth_header = self._api_key
        if not auth_header.startswith('Bearer '):
            auth_header = f'Bearer {auth_header}'
            
        auth_header = auth_header.strip()

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': auth_header,
            # ✅ FIX: اضافه کردن User-Agent برای جلوگیری از ارور 401
            'User-Agent': 'BeauClub-App/1.0 (Shahkar-Verifier)',
        }

        try:
            # 🔍 لاگ‌های دقیق برای دیباگ نهایی
            logger.info(f"🔍 [Shahkar] URL: {self._api_url}")
            logger.info(f"🔍 [Shahkar] Payload: {payload}")
            
            # لاگ کردن طول توکن و پیش‌نمایش
            token_len = len(auth_header)
            token_preview = f"{auth_header[:15]}...{auth_header[-10:]}" if token_len > 25 else auth_header
            logger.info(f"🔍 [Shahkar] Auth Header Length: {token_len}")
            logger.info(f"🔍 [Shahkar] Auth Header Preview: {token_preview}")
            
            # 🔍 لاگ کامل توکن فقط برای دیباگ (بعد از حل مشکل حذف کنید)
            logger.warning(f"🔍 [Shahkar] FULL AUTH HEADER (DEBUG): {auth_header}")

            response = requests.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=15
            )

            logger.info(f"🔍 [Shahkar] Response Status: {response.status_code}")
            logger.info(f"🔍 [Shahkar] Response Body: {response.text}")

            if response.status_code == 200:
                data = response.json()
                
                api_success = data.get('success', False)
                match_result = data.get('data')
                api_message = data.get('message')

                if api_success:
                    if match_result is True:
                        return VerificationResult(
                            success=True,
                            verified_name=full_name or '',
                            national_id=national_id,
                        )
                    else:
                        return VerificationResult(
                            success=False,
                            error_message=api_message or 'کد ملی با شماره موبایل مطابقت ندارد',
                            error_code='SHAHKAR_MISMATCH',
                            national_id=national_id
                        )
                else:
                    return VerificationResult(
                        success=False,
                        error_message=api_message or 'خطا در سرویس استعلام شاهکار',
                        error_code='SHAHKAR_API_ERROR',
                        national_id=national_id
                    )

            elif response.status_code == 401:
                 return VerificationResult(
                    success=False,
                    error_message='توکن احراز هویت شاهکار نامعتبر است (IP یا توکن را در پنل api.ir چک کنید)',
                    error_code='SHAHKAR_UNAUTHORIZED'
                )
            else:
                 return VerificationResult(
                    success=False,
                    error_message=f'خطای سرور استعلام (کد: {response.status_code})',
                    error_code='SHAHKAR_HTTP_ERROR'
                )

        except requests.Timeout:
            logger.error("Shahkar API Timeout")
            return VerificationResult(
                success=False,
                error_message='زمان اتصال به سرویس استعلام به پایان رسید',
                error_code='SHAHKAR_TIMEOUT'
            )
        except Exception as e:
            logger.error(f"Shahkar API Exception: {e}")
            return VerificationResult(
                success=False,
                error_message='خطا در ارتباط با سرویس استعلام',
                error_code='SHAHKAR_CONNECTION_ERROR'
            )