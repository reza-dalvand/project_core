# shared/sms/console.py

"""
Kavenegar Console SMS Provider

این provider برای محیط توسعه/تست استفاده می‌شود.
از نظر معماری جایگزین سرویس کاوه‌نگار است، اما به جای ارسال واقعی پیامک،
پیام‌ها را در کنسول چاپ می‌کند تا توسعه‌دهنده بتواند کدها و پیام‌ها را ببیند.
"""
import json
import uuid
from typing import List, Optional

from .base import AbstractSmsProvider, SmsResult, BulkSmsResult


class KavenegarConsoleSmsProvider(AbstractSmsProvider):
    """شبیه‌ساز کاوه‌نگار برای محیط توسعه — فقط چاپ در کنسول"""

    def __init__(self):
        self._sent_messages = []
        self._credit = 100000

    def _generate_message_id(self, prefix: str = 'CONSOLE') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:12]}'

    def _log_sms(self, send_type: str, phone: str, message_id: str, message: str):
        separator = '═' * 70
        print(
            f'\n{separator}\n'
            f'📱 [KAVENEGAR-CONSOLE] {send_type} → {phone}\n'
            f'message_id: {message_id}\n\n'
            f'{message}\n'
            f'{separator}\n'
        )

    def send_otp(self, phone: str, message: str) -> SmsResult:
        phone = self.validate_phone(phone)
        message_id = self._generate_message_id('CONSOLE-OTP')

        self._sent_messages.append({
            'phone': phone,
            'message': message,
            'type': 'otp',
            'message_id': message_id,
        })

        self._log_sms('OTP', phone, message_id, message)

        return SmsResult(success=True, message_id=message_id, cost=0)

    def send(self, phone: str, message: str, sender: str = '') -> SmsResult:
        phone = self.validate_phone(phone)
        message_id = self._generate_message_id('CONSOLE-SMS')

        self._sent_messages.append({
            'phone': phone,
            'message': message,
            'sender': sender,
            'type': 'simple',
            'message_id': message_id,
        })

        self._log_sms('SMS', phone, message_id, message)

        return SmsResult(success=True, message_id=message_id, cost=0)

    def send_pattern(self, phone: str, template_name: str, **variables) -> SmsResult:
        phone = self.validate_phone(phone)
        message_id = self._generate_message_id('CONSOLE-PATTERN')

        printable_variables = variables or {}

        if 'token' in printable_variables:
            message = f'کد تایید: {printable_variables["token"]}'
        elif 'code' in printable_variables:
            message = f'کد تایید: {printable_variables["code"]}'
        else:
            message = (
                f'قالب: {template_name}\n'
                f'متغیرها: {json.dumps(printable_variables, ensure_ascii=False)}'
            )

        self._sent_messages.append({
            'phone': phone,
            'template': template_name,
            'variables': printable_variables,
            'message': message,
            'type': 'pattern',
            'message_id': message_id,
        })

        self._log_sms('PATTERN', phone, message_id, message)

        return SmsResult(success=True, message_id=message_id, cost=0)

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
                continue

        if not valid_recipients:
            return BulkSmsResult(
                success=False,
                error_message='هیچ شماره معتبری یافت نشد',
            )

        message_ids = []

        for index, phone in enumerate(valid_recipients):
            message = ''
            if messages:
                message = messages[index] if index < len(messages) else messages[-1]

            message_id = self._generate_message_id('CONSOLE-BULK')
            message_ids.append(message_id)

            self._sent_messages.append({
                'phone': phone,
                'message': message,
                'type': 'bulk',
                'message_id': message_id,
            })

            self._log_sms('BULK', phone, message_id, message)

        return BulkSmsResult(
            success=True,
            total_sent=len(valid_recipients),
            total_failed=len(recipients) - len(valid_recipients),
            total_cost=0,
            message_ids=message_ids,
        )

    def get_credit(self) -> int:
        return self._credit

    # ─── متدهای کمکی برای تست/توسعه ───
    def get_sent_messages(self) -> list:
        return self._sent_messages

    def get_last_message(self, phone: str) -> Optional[str]:
        for item in reversed(self._sent_messages):
            if item.get('phone') == phone:
                return item.get('message', '')
        return None

    def clear(self):
        self._sent_messages.clear()