"""
Kavenegar SMS Provider برای محیط پروداکشن
مستندات: https://kavenegar.com/rest.html
"""
import logging
from typing import Optional

from .base import AbstractSmsProvider, SmsResult

logger = logging.getLogger(__name__)


class KavenegarSmsProvider(AbstractSmsProvider):
    """
    ارسال پیامک از طریق کاوه‌نگار
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError('KAVENEGAR_API_KEY تنظیم نشده است')
        self._api_key = api_key
        self._api = None

    @property
    def api(self):
        """Lazy init برای KavenegarAPI"""
        if self._api is None:
            try:
                from kavenegar import KavenegarAPI
                self._api = KavenegarAPI(self._api_key)
            except ImportError:
                raise ImportError(
                    'پکیج kavenegar نصب نیست. '
                    'نصب کنید: pip install kavenegar'
                )
        return self._api

    def send(self, phone: str, message: str) -> SmsResult:
        phone = self.validate_phone(phone)
        try:
            params = {
                'receptor': phone,
                'message': message,
            }
            response = self.api.sms_send(params)
            entry = response['entries'][0]

            return SmsResult(
                success=True,
                message_id=str(entry['messageid']),
                cost=entry.get('cost', 0),
            )

        except Exception as e:
            logger.error(f"Kavenegar send error → {phone}: {e}")
            return SmsResult(
                success=False,
                error_message=str(e),
            )

    def send_pattern(
        self,
        phone: str,
        template_name: str,
        **kwargs
    ) -> SmsResult:
        phone = self.validate_phone(phone)
        try:
            params = {
                'receptor': phone,
                'template': template_name,
                **kwargs,
            }
            response = self.api.verify_lookup(params)
            entry = response['entries']

            return SmsResult(
                success=True,
                message_id=str(entry.get('messageid', '')),
                cost=entry.get('cost', 0),
            )

        except Exception as e:
            logger.error(
                f"Kavenegar pattern error → {phone}, "
                f"template={template_name}: {e}"
            )
            return SmsResult(
                success=False,
                error_message=str(e),
            )

    def send_otp(self, phone: str, code: str) -> SmsResult:
        return self.send_pattern(
            phone=phone,
            template_name='zibano-otp',
            token=code,
        )

    def get_credit(self) -> int:
        try:
            response = self.api.account_info()
            return response.get('remaincredit', 0)
        except Exception as e:
            logger.error(f"Kavenegar credit error: {e}")
            return 0