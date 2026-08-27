"""
Mock SMS Provider برای محیط توسعه
بدون ارسال واقعی — فقط لاگ در کنسول
"""
import logging
from typing import List, Optional
from .base import AbstractSmsProvider, SmsResult, BulkSmsResult

logger = logging.getLogger(__name__)


class MockSmsProvider(AbstractSmsProvider):
    """
    Provider تقلبی برای توسعه
    پیامک‌ها را در کنسول چاپ می‌کند
    """

    def __init__(self):
        self._sent_messages = []
        self._credit = 100000

    def send_otp(self, phone: str, template_name: str, token: str) -> SmsResult:
        phone = self.validate_phone(phone)
        message_id = f'MOCK-{len(self._sent_messages) + 1}'

        self._sent_messages.append({
            'phone': phone,
            'template': template_name,
            'token': token,
            'type': 'otp',
        })

        logger.info(
            f"🔑 [MOCK OTP] → {phone}\n"
            f"   قالب: {template_name}\n"
            f"   کد: {token}\n"
            f"   شناسه: {message_id}"
        )

        return SmsResult(
            success=True,
            message_id=message_id,
            cost=250,
        )

    def send_pattern(self, phone: str, template_name: str, **kwargs) -> SmsResult:
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

    def send(self, phone: str, message: str, sender: str = '') -> SmsResult:
        phone = self.validate_phone(phone)
        message_id = f'MOCK-{len(self._sent_messages) + 1}'

        self._sent_messages.append({
            'phone': phone,
            'message': message,
            'sender': sender,
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

    def send_bulk(
        self,
        recipients: List[str],
        messages: List[str],
        senders: List[str] = None,
    ) -> BulkSmsResult:
        if not recipients:
            return BulkSmsResult(
                success=False,
                error_message='لیست دریافت‌کنندگان خالی است',
            )

        valid_recipients = []
        for phone in recipients:
            try:
                valid_recipients.append(self.validate_phone(phone))
            except ValueError:
                pass

        if not valid_recipients:
            return BulkSmsResult(
                success=False,
                error_message='هیچ شماره معتبری یافت نشد',
            )

        message_ids = []
        total_cost = 0

        for i, phone in enumerate(valid_recipients):
            message_id = f'MOCK-BULK-{len(self._sent_messages) + 1}'
            message_ids.append(message_id)
            total_cost += 250

            self._sent_messages.append({
                'phone': phone,
                'message': messages[i] if i < len(messages) else messages[-1],
                'type': 'bulk',
            })

            logger.info(
                f"📢 [MOCK BULK SMS] → {phone}\n"
                f"   متن: {messages[i] if i < len(messages) else messages[-1]}\n"
                f"   شناسه: {message_id}"
            )

        return BulkSmsResult(
            success=True,
            total_sent=len(valid_recipients),
            total_failed=0,
            total_cost=total_cost,
            message_ids=message_ids,
        )

    def get_credit(self) -> int:
        return self._credit

    # ─── متدهای کمکی برای تست ───
    def get_sent_messages(self) -> list:
        return self._sent_messages

    def get_last_otp(self, phone: str) -> Optional[str]:
        for msg in reversed(self._sent_messages):
            if msg.get('phone') == phone and msg.get('type') == 'otp':
                return msg.get('token')
        return None

    def clear(self):
        self._sent_messages.clear()