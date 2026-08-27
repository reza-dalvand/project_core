"""
ZarinPal Payment Gateway
مستندات: https://docs.zarinpal.com/

فرمت Callback زرین‌پال:
  ?Authority=xxx&Status=OK
  ?Authority=xxx&Status=NOK
"""
import logging
import requests
from typing import Optional
from .base import AbstractPaymentGateway, PaymentRequestResult, PaymentVerifyResult

logger = logging.getLogger(__name__)


class ZarinPalGateway(AbstractPaymentGateway):
    """
    درگاه پرداخت زرین‌پال (نسخه ۴)
    """
    BASE_URL_SANDBOX = 'https://sandbox.zarinpal.com/pg/v4/payment'
    BASE_URL_REAL    = 'https://api.zarinpal.com/pg/v4/payment'
    START_URL        = 'https://www.zarinpal.com/pg/StartPay/'

    RESULT_SUCCESS           = 100
    RESULT_ALREADY_VERIFIED  = 101

    STATUS_MESSAGES = {
        100: 'تراکنش با موفقیت تایید شد',
        101: 'تراکنش قبلاً تایید شده',
        -9:  'خطای اعتبارسنجی',
        -10: 'کاربر مسدود شده',
        -11: 'درخواست یافت نشد',
        -12: 'امکان ویرایش نیست',
        -21: 'عملیات مالی ناموفق بود',
        -22: 'خطای ناشناخته',
        -33: 'مبلغ با مبلغ تراکنش مطابقت ندارد',
        -54: 'درخواست آرشیو شده',
        2:   'خطای ناشناخته داخلی',
        3:   'خطای اعتبارسنجی',
        4:   'کاربر مسدود شده است',
        5:   'مبلغ باید بیشتر از ۱۰,۰۰۰ ریال باشد',
        6:   'کمتر از حد مجاز برداشت است',
        7:   'مرچنت غیرفعال است',
        8:   'خطا در ارسال اطلاعات',
        9:   'کاربر معتبر نیست',
        10:  'کاربر مسدود شده',
        11:  'درخواست یافت نشد',
        12:  'امکان ویرایش نیست',
    }

    def __init__(self, merchant_id: str, sandbox: bool = True):
        if not merchant_id:
            raise ValueError('ZARINPAL_MERCHANT_ID تنظیم نشده است')
        self._merchant_id = merchant_id
        self._sandbox     = sandbox
        self._base_url    = self.BASE_URL_SANDBOX if sandbox else self.BASE_URL_REAL

    def get_gateway_name(self) -> str:
        return 'zarinpal'

    # ═══════════════════════════════════════════════
    #   ایجاد تراکنش
    # ═══════════════════════════════════════════════
    def create_payment(
        self,
        amount_toman: int,
        callback_url: str,
        description: str = '',
        order_id: str = '',
        mobile: str = '',
    ) -> PaymentRequestResult:
        self.validate_amount(amount_toman)

        payload: dict = {
            'merchant_id': self._merchant_id,
            'amount':      amount_toman,
            'callback_url': callback_url,
            'description': description or 'پرداخت بیو کلاب',
        }

        # متادیتا (اختیاری)
        metadata: dict = {}
        if order_id:
            metadata['order_id'] = str(order_id)
        if mobile:
            metadata['mobile'] = mobile
        if metadata:
            payload['metadata'] = metadata

        try:
            response = requests.post(
                f'{self._base_url}/request.json',
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            result_code = data.get('data', {}).get('code', 0)

            if result_code == self.RESULT_SUCCESS:
                authority = data['data']['authority']
                return PaymentRequestResult(
                    success=True,
                    payment_url=f'{self.START_URL}{authority}',
                    track_id=authority,
                )

            error_msg = data.get('errors', {}).get(
                'message', 'خطا در ایجاد تراکنش زرین‌پال'
            )
            return PaymentRequestResult(
                success=False,
                error_message=error_msg,
            )

        except requests.Timeout:
            return PaymentRequestResult(
                success=False,
                error_message='زمان ارتباط با زرین‌پال به پایان رسید',
            )
        except requests.RequestException as e:
            logger.error(f"ZarinPal create_payment error: {e}")
            return PaymentRequestResult(
                success=False,
                error_message='خطا در ارتباط با درگاه زرین‌پال',
            )

    # ═══════════════════════════════════════════════
    #   تایید تراکنش
    # ═══════════════════════════════════════════════
    def verify_payment(
        self,
        track_id: str,
        amount_toman: int,
    ) -> PaymentVerifyResult:
        payload = {
            'merchant_id': self._merchant_id,
            'amount':      amount_toman,
            'authority':   track_id,
        }

        try:
            response = requests.post(
                f'{self._base_url}/verify.json',
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            result_code = data.get('data', {}).get('code', 0)

            if result_code in [self.RESULT_SUCCESS, self.RESULT_ALREADY_VERIFIED]:
                return PaymentVerifyResult(
                    success=True,
                    ref_number=str(data['data'].get('ref_id', '')),
                    card_number=str(data['data'].get('card_pan', '')),
                    paid_amount=data['data'].get('amount', 0),
                    status_code=result_code,
                )

            error_msg = data.get('errors', {}).get('message', 'تراکنش ناموفق')
            return PaymentVerifyResult(
                success=False,
                error_message=error_msg,
                status_code=result_code,
            )

        except requests.Timeout:
            return PaymentVerifyResult(
                success=False,
                error_message='زمان تایید تراکنش به پایان رسید',
            )
        except requests.RequestException as e:
            logger.error(f"ZarinPal verify_payment error: {e}")
            return PaymentVerifyResult(
                success=False,
                error_message='خطا در تایید تراکنش زرین‌پال',
            )