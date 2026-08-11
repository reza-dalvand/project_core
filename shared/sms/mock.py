"""
Mock SMS Provider برای محیط توسعه
بدون ارسال واقعی — فقط لاگ در کنسول
"""
import logging
from typing import Optional

from .base import AbstractSmsProvider, SmsResult

logger = logging.getLogger(__name__)


class MockSmsProvider(AbstractSmsProvider):
    """
    Provider تقلبی برای توسعه
    پیامک‌ها را در کنسول چاپ می‌کند
    """

    def __init__(self):
        self._sent_messages = []  # برای تست
        self._credit = 100000

    def send(self, phone: str, message: str) -> SmsResult:
        phone = self.validate_phone(phone)
        message_id = f'MOCK-{len(self._sent_messages) + 1}'

        self._sent_messages.append({
            'phone': phone,
            'message': message,
            'type': 'simple',
        })

        logger.info(
            f"📱 [MOCK SMS] → {phone}\n"
            f"   متن: {message}\n"
            f"   شناسه: {message_id}"
        )

        return SmsResult(
            success=True,
            message_id=message_id,
            cost=250,
        )

    def send_pattern(
        self,
        phone: str,
        template_name: str,
        **kwargs
    ) -> SmsResult:
        phone = self.validate_phone(phone)
        message_id = f'MOCK-{len(self._sent_messages) + 1}'

        self._sent_messages.append({
            'phone': phone,
            'template': template_name,
            'variables': kwargs,
            'type': 'pattern',
        })

        logger.info(
            f"📱 [MOCK SMS Pattern] → {phone}\n"
            f"   قالب: {template_name}\n"
            f"   متغیرها: {kwargs}\n"
            f"   شناسه: {message_id}"
        )

        return SmsResult(
            success=True,
            message_id=message_id,
            cost=250,
        )

    def send_otp(self, phone: str, code: str) -> SmsResult:
        phone = self.validate_phone(phone)
        message_id = f'MOCK-{len(self._sent_messages) + 1}'

        self._sent_messages.append({
            'phone': phone,
            'code': code,
            'type': 'otp',
        })

        logger.info(
            f"🔑 [MOCK OTP] → {phone}\n"
            f"   کد: {code}\n"
            f"   شناسه: {message_id}"
        )

        return SmsResult(
            success=True,
            message_id=message_id,
            cost=250,
        )

    def get_credit(self) -> int:
        return self._credit

    # ─── متدهای کمکی برای تست ───

    def get_sent_messages(self) -> list:
        return self._sent_messages

    def get_last_otp(self, phone: str) -> Optional[str]:
        for msg in reversed(self._sent_messages):
            if msg.get('phone') == phone and msg.get('type') == 'otp':
                return msg.get('code')
        return None

    def clear(self):
        self._sent_messages.clear()