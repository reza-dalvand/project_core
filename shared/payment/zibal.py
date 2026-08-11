"""
Zibal Payment Gateway
مستندات: https://docs.zibal.ir/
"""
import logging
import requests
from typing import Optional

from .base import (
    AbstractPaymentGateway,
    PaymentRequestResult,
    PaymentVerifyResult,
)

logger = logging.getLogger(__name__)


class ZibalGateway(AbstractPaymentGateway):
    """
    درگاه پرداخت زیبال
    """

    BASE_URL = 'https://gateway.zibal.ir/v1'
    START_URL = 'https://gate.zibal.ir/start/'

    RESULT_SUCCESS = 100
    RESULT_ALREADY_VERIFIED = 201

    STATUS_MESSAGES = {
        100: 'تراکنش با موفقیت تایید شد',
        102: 'merchant یافت نشد',
        103: 'merchant غیرفعال است',
        104: 'merchant نامعتبر است',
        105: 'مبلغ باید بیشتر از ۱۰۰۰ تومان باشد',
        106: 'callbackUrl نامعتبر است',
        113: 'مبلغ تراکنش از سقف محدود فراتر است',
        201: 'قبلاً تایید شده',
        202: 'سفارش پرداخت نشده یا ناموفق بوده',
    }

    def __init__(self, merchant_id: str):
        if not merchant_id:
            raise ValueError('ZIBAL_MERCHANT_ID تنظیم نشده است')
        self._merchant_id = merchant_id

    def get_gateway_name(self) -> str:
        return 'zibal'

    def create_payment(
        self,
        amount_toman: int,
        callback_url: str,
        description: str = '',
        order_id: str = '',
        mobile: str = '',
    ) -> PaymentRequestResult:
        self.validate_amount(amount_toman)
        amount_rial = amount_toman * 10

        payload = {
            'merchant': self._merchant_id,
            'amount': amount_rial,
            'callbackUrl': callback_url,
            'description': description or 'پرداخت زیبانو',
        }
        if order_id:
            payload['orderId'] = str(order_id)
        if mobile:
            payload['mobile'] = mobile

        try:
            response = requests.post(
                f'{self.BASE_URL}/request',
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if data.get('result') == self.RESULT_SUCCESS:
                track_id = str(data.get('trackId'))
                return PaymentRequestResult(
                    success=True,
                    payment_url=f'{self.START_URL}{track_id}',
                    track_id=track_id,
                )

            error_msg = self.STATUS_MESSAGES.get(
                data.get('result', 0),
                data.get('message', 'خطا در ایجاد تراکنش'),
            )
            return PaymentRequestResult(
                success=False,
                error_message=error_msg,
            )

        except requests.Timeout:
            return PaymentRequestResult(
                success=False,
                error_message='زمان ارتباط با درگاه به پایان رسید',
            )
        except requests.RequestException as e:
            logger.error(f"Zibal create_payment error: {e}")
            return PaymentRequestResult(
                success=False,
                error_message='خطا در ارتباط با درگاه پرداخت',
            )

    def verify_payment(
        self,
        track_id: str,
        amount_toman: int,
    ) -> PaymentVerifyResult:
        payload = {
            'merchant': self._merchant_id,
            'trackId': track_id,
        }

        try:
            response = requests.post(
                f'{self.BASE_URL}/verify',
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            result_code = data.get('result', 0)
            if result_code in [
                self.RESULT_SUCCESS,
                self.RESULT_ALREADY_VERIFIED,
            ]:
                paid_rial = data.get('amount', 0)
                paid_toman = paid_rial // 10

                if paid_toman != amount_toman:
                    return PaymentVerifyResult(
                        success=False,
                        error_message='مبلغ پرداختی مطابقت ندارد',
                        status_code=result_code,
                    )

                return PaymentVerifyResult(
                    success=True,
                    ref_number=str(data.get('refNumber', '')),
                    card_number=data.get('cardNumber', ''),
                    paid_amount=paid_toman,
                    status_code=result_code,
                )

            error_msg = self.STATUS_MESSAGES.get(
                result_code, 'تراکنش ناموفق'
            )
            return PaymentVerifyResult(
                success=False,
                error_message=error_msg,
                status_code=result_code,
            )

        except requests.RequestException as e:
            logger.error(f"Zibal verify_payment error: {e}")
            return PaymentVerifyResult(
                success=False,
                error_message='خطا در تایید تراکنش',
            )