"""
Abstract SMS Provider
الگوی Strategy Pattern برای سرویس‌دهنده‌های پیامک
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SmsResult:
    """نتیجه ارسال پیامک"""
    success: bool
    message_id: Optional[str] = None
    cost: int = 0
    error_message: str = ''


class AbstractSmsProvider(ABC):
    """
    کلاس پایه انتزاعی برای ارسال پیامک
    هر provider باید این کلاس را پیاده‌سازی کند
    """

    @abstractmethod
    def send(self, phone: str, message: str) -> SmsResult:
        """ارسال پیامک ساده"""
        ...

    @abstractmethod
    def send_pattern(
        self,
        phone: str,
        template_name: str,
        **kwargs
    ) -> SmsResult:
        """ارسال پیامک قالبی (Pattern/Template)"""
        ...

    @abstractmethod
    def send_otp(self, phone: str, code: str) -> SmsResult:
        """ارسال کد تایید یکبار مصرف"""
        ...

    @abstractmethod
    def get_credit(self) -> int:
        """دریافت اعتبار باقیمانده"""
        ...

    def validate_phone(self, phone: str) -> str:
        """اعتبارسنجی و نرمال‌سازی شماره موبایل"""
        phone = phone.strip()
        phone = phone.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))
        phone = phone.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')

        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('0098'):
            phone = '0' + phone[4:]

        if not phone.startswith('09') or len(phone) != 11:
            raise ValueError(f'شماره موبایل نامعتبر: {phone}')

        return phone