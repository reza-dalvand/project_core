"""
Zibal Payment Gateway Service
درگاه پرداخت زیبال
"""
import logging
import requests
from django.conf import settings
from apps.core.exceptions import PaymentException

logger = logging.getLogger(__name__)


class ZibalService:
    """
    سرویس پرداخت زیبال
    مستندات: https://docs.zibal.ir/
    """

    START_URL = 'https://gate.zibal.ir/start/'
    VERIFY_URL = 'https://verify.zibal.ir/verify/'
    REQUEST_URL = 'https://gateway.zibal.ir/v1/request'
    VERIFY_API_URL = 'https://gateway.zibal.ir/v1/verify'

    # کدهای وضعیت زیبال
    STATUS_SUCCESS = 100
    STATUS_VERIFIED = 100
    STATUS_ALREADY_VERIFIED = 201

    @classmethod
    def create_payment(cls, amount: int, callback_url: str, description: str = '',
                       order_id: str = '', mobile: str = '', **kwargs):
        """
        ایجاد تراکنش پرداخت
        """
        try:
            payload = {
                'merchant': settings.ZIBAL_MERCHANT_ID,
                'amount': amount,  # به ریال
                'callbackUrl': callback_url,
                'description': description,
                'orderId': order_id,
            }

            if mobile:
                payload['mobile'] = mobile

            # فیلدهای اضافی
            for key, value in kwargs.items():
                payload[key] = value

            response = requests.post(
                cls.REQUEST_URL,
                json=payload,
                timeout=30,
            )

            data = response.json()

            if data.get('result') == 100:
                track_id = data.get('trackId')
                payment_url = f'{cls.START_URL}{track_id}'

                return {
                    'success': True,
                    'track_id': track_id,
                    'payment_url': payment_url,
                    'amount': amount,
                }
            else:
                error_msg = data.get('message', 'خطا در ایجاد تراکنش')
                raise PaymentException(message=error_msg, details=data)

        except requests.Timeout:
            raise PaymentException(message='زمان ارتباط با درگاه به پایان رسید')
        except requests.RequestException as e:
            logger.error(f"Zibal request error: {e}")
            raise PaymentException(message='خطا در ارتباط با درگاه پرداخت')
        except PaymentException:
            raise
        except Exception as e:
            logger.exception(f"Zibal create payment error: {e}")
            raise PaymentException(message='خطای غیرمنتظره در ایجاد تراکنش')

    @classmethod
    def verify_payment(cls, track_id: int, amount: int):
        """
        تایید تراکنش پرداخت
        """
        try:
            payload = {
                'merchant': settings.ZIBAL_MERCHANT_ID,
                'trackId': track_id,
            }

            response = requests.post(
                cls.VERIFY_API_URL,
                json=payload,
                timeout=30,
            )

            data = response.json()
            result = data.get('result')

            if result in [cls.STATUS_VERIFIED, cls.STATUS_ALREADY_VERIFIED]:
                # بررسی مبلغ
                paid_amount = data.get('amount', 0)
                if paid_amount != amount:
                    raise PaymentException(
                        message='مبلغ پرداختی با مبلغ تراکنش مطابقت ندارد',
                        details={'expected': amount, 'paid': paid_amount}
                    )

                return {
                    'success': True,
                    'track_id': track_id,
                    'ref_number': data.get('refNumber', ''),
                    'card_number': data.get('cardNumber', ''),
                    'paid_amount': paid_amount,
                    'status': data.get('status'),
                    'paid_at': data.get('paidAt'),
                }
            else:
                error_msg = data.get('message', 'تراکنش ناموفق')
                raise PaymentException(
                    message=error_msg,
                    code='PAYMENT_FAILED',
                    details=data
                )

        except requests.Timeout:
            raise PaymentException(message='زمان تایید تراکنش به پایان رسید')
        except requests.RequestException as e:
            logger.error(f"Zibal verify error: {e}")
            raise PaymentException(message='خطا در تایید تراکنش')
        except PaymentException:
            raise
        except Exception as e:
            logger.exception(f"Zibal verify payment error: {e}")
            raise PaymentException(message='خطای غیرمنتظره در تایید تراکنش')

    @classmethod
    def inquiry(cls, track_id: int):
        """
        استعلام وضعیت تراکنش
        """
        try:
            payload = {
                'merchant': settings.ZIBAL_MERCHANT_ID,
                'trackId': track_id,
            }

            response = requests.post(
                'https://gateway.zibal.ir/v1/inquiry',
                json=payload,
                timeout=30,
            )

            return response.json()

        except Exception as e:
            logger.error(f"Zibal inquiry error: {e}")
            return {'result': -1, 'message': str(e)}