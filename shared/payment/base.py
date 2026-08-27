"""
Abstract Payment Gateway
الگوی Strategy Pattern برای درگاه‌های پرداخت
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PaymentRequestResult:
    """نتیجه ایجاد تراکنش"""
    success: bool
    payment_url: str = ''
    track_id: Optional[str] = None
    error_message: str = ''


@dataclass
class PaymentVerifyResult:
    """نتیجه تایید تراکنش"""
    success: bool
    ref_number: str = ''
    card_number: str = ''
    paid_amount: int = 0  # تومان
    status_code: int = 0
    error_message: str = ''


class AbstractPaymentGateway(ABC):
    """
    کلاس پایه انتزاعی برای درگاه پرداخت
    """

    @abstractmethod
    def create_payment(
        self,
        amount_toman: int,
        callback_url: str,
        description: str = '',
        order_id: str = '',
        mobile: str = '',
    ) -> PaymentRequestResult:
        """ایجاد تراکنش و دریافت URL پرداخت"""
        ...

    @abstractmethod
    def verify_payment(
        self,
        track_id: str,
        amount_toman: int,
    ) -> PaymentVerifyResult:
        """تایید تراکنش پس از بازگشت کاربر"""
        ...

    @abstractmethod
    def get_gateway_name(self) -> str:
        """نام درگاه"""
        ...

    def validate_amount(self, amount_toman: int) -> None:
        """اعتبارسنجی مبلغ"""
        if amount_toman < 1000:
            raise ValueError('حداقل مبلغ پرداخت ۱,۰۰۰ تومان است')
        if amount_toman > 500_000_000:
            raise ValueError('مبلغ پرداخت بیش از حد مجاز است')