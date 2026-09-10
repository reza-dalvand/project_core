"""
Abstract SMS Provider
الگوی Strategy Pattern برای سرویس‌دهنده‌های پیامک

متدهای اصلی:
- send_otp: پیامک کد تایید
- send: پیام ساده اطلاع‌رسانی
- send_pattern: ارسال با قالب/پترن
- send_bulk: ارسال گروهی
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SmsResult:
    """نتیجه ارسال پیامک"""
    success: bool
    message_id: Optional[str] = None
    cost: int = 0
    error_message: str = ''


@dataclass
class BulkSmsResult:
    """نتیجه ارسال گروهی پیامک"""
    success: bool
    total_sent: int = 0
    total_failed: int = 0
    total_cost: int = 0
    message_ids: List[str] = field(default_factory=list)
    error_message: str = ''


class AbstractSmsProvider(ABC):
    """
    کلاس پایه انتزاعی برای ارسال پیامک
    هر provider باید این کلاس را پیاده‌سازی کند
    """

    @abstractmethod
    def send_otp(self, phone: str, message: str) -> SmsResult:
        """ارسال پیامک حاوی کد تایید"""
        ...

    @abstractmethod
    def send(self, phone: str, message: str, sender: str = '') -> SmsResult:
        """ارسال پیامک ساده"""
        ...

    @abstractmethod
    def send_pattern(self, phone: str, template_name: str, **variables) -> SmsResult:
        """ارسال از طریق قالب/پترن سرویس‌دهنده"""
        ...

    @abstractmethod
    def send_bulk(
        self,
        recipients: List[str],
        messages: List[str],
        senders: List[str] = None,
    ) -> BulkSmsResult:
        """ارسال گروهی پیامک"""
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