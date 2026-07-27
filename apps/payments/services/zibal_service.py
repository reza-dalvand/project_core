"""
سرویس درگاه پرداخت زیبال (Zibal)
مستندات: https://docs.zibal.ir/
"""
import logging
import requests
from decimal import Decimal
from django.conf import settings

from apps.core.exceptions import PaymentException

logger = logging.getLogger(__name__)


class ZibalService:
    """
    سرویس کامل درگاه پرداخت زیبال
    """

    BASE_URL = 'https://gateway.zibal.ir/v1'
    START_URL = 'https://gate.zibal.ir/start/'

    # کدهای وضعیت زیبال
    RESULT_SUCCESS = 100
    RESULT_ALREADY_VERIFIED = 201
    RESULT_NOT_PAID = 110

    # نگاشت کدهای وضعیت به پیام فارسی
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

    @classmethod
    def _get_merchant_id(cls):
        merchant_id = getattr(settings, 'ZIBAL_MERCHANT_ID', 'zibal')
        if not merchant_id:
            raise PaymentException(
                message='تنظیمات درگاه پرداخت کامل نیست',
                code='GATEWAY_NOT_CONFIGURED',
            )
        return merchant_id

    @classmethod
    def create_payment(
        cls,
        amount_toman: int,
        callback_url: str,
        description: str = '',
        order_id: str = '',
        mobile: str = '',
        email: str = '',
        allowed_cards: list = None,
    ) -> dict:
        """
        ایجاد تراکنش پرداخت در زیبال

        Args:
            amount_toman: مبلغ به تومان
            callback_url: آدرس بازگشت
            description: توضیحات
            order_id: شناسه سفارش (اختیاری)
            mobile: شماره موبایل (برای نمایش کارت‌های معتبر)
            email: ایمیل (اختیاری)
            allowed_cards: لیست کارت‌های مجاز (اختیاری)

        Returns:
            dict: {
                'success': True,
                'track_id': int,
                'payment_url': str,
                'amount': int,
            }
        """
        # اعتبارسنجی مبلغ
        if amount_toman < 1000:
            raise PaymentException(
                message='حداقل مبلغ پرداخت ۱,۰۰۰ تومان است',
                code='MIN_AMOUNT',
            )

        # تبدیل تومان به ریال (زیبال ریال قبول می‌کند)
        amount_rial = amount_toman * 10

        merchant_id = cls._get_merchant_id()

        payload = {
            'merchant': merchant_id,
            'amount': amount_rial,
            'callbackUrl': callback_url,
            'description': description or 'پرداخت زیبانو',
        }

        if order_id:
            payload['orderId'] = str(order_id)
        if mobile:
            payload['mobile'] = mobile
        if email:
            payload['email'] = email
        if allowed_cards:
            payload['allowedCards'] = allowed_cards

        try:
            response = requests.post(
                f'{cls.BASE_URL}/request',
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            result_code = data.get('result', 0)

            if result_code == cls.RESULT_SUCCESS:
                track_id = data.get('trackId')
                payment_url = f'{cls.START_URL}{track_id}'

                logger.info(
                    f"Zibal payment created: trackId={track_id}, "
                    f"amount={amount_toman} toman"
                )

                return {
                    'success': True,
                    'track_id': track_id,
                    'payment_url': payment_url,
                    'amount': amount_toman,
                    'amount_rial': amount_rial,
                }
            else:
                error_msg = cls.STATUS_MESSAGES.get(
                    result_code,
                    data.get('message', 'خطا در ایجاد تراکنش')
                )
                raise PaymentException(
                    message=error_msg,
                    code=f'ZIBAL_{result_code}',
                    details=data,
                )

        except requests.Timeout:
            raise PaymentException(
                message='زمان ارتباط با درگاه به پایان رسید. لطفاً دوباره تلاش کنید',
                code='GATEWAY_TIMEOUT',
            )
        except requests.ConnectionError:
            raise PaymentException(
                message='خطا در اتصال به درگاه پرداخت. لطفاً اتصال اینترنت خود را بررسی کنید',
                code='GATEWAY_CONNECTION_ERROR',
            )
        except requests.RequestException as e:
            logger.error(f"Zibal request error: {e}")
            raise PaymentException(
                message='خطا در ارتباط با درگاه پرداخت',
                code='GATEWAY_ERROR',
            )

    @classmethod
    def verify_payment(cls, track_id: int, expected_amount_toman: int) -> dict:
        """
        تایید تراکنش پرداخت در زیبال

        Args:
            track_id: شناسه تراکنش زیبال
            expected_amount_toman: مبلغ مورد انتظار به تومان

        Returns:
            dict: {
                'success': True,
                'track_id': int,
                'ref_number': str,
                'card_number': str,
                'paid_amount': int,  # تومان
                'status': int,
                'paid_at': str,
                'message': str,
            }
        """
        merchant_id = cls._get_merchant_id()

        payload = {
            'merchant': merchant_id,
            'trackId': track_id,
        }

        try:
            response = requests.post(
                f'{cls.BASE_URL}/verify',
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            result_code = data.get('result', 0)

            if result_code in [cls.RESULT_SUCCESS, cls.RESULT_ALREADY_VERIFIED]:
                # مبلغ پرداختی (ریال → تومان)
                paid_amount_rial = data.get('amount', 0)
                paid_amount_toman = paid_amount_rial // 10

                # بررسی مبلغ
                if paid_amount_toman != expected_amount_toman:
                    logger.warning(
                        f"Zibal amount mismatch: expected={expected_amount_toman}, "
                        f"paid={paid_amount_toman}"
                    )
                    raise PaymentException(
                        message='مبلغ پرداختی با مبلغ تراکنش مطابقت ندارد',
                        code='AMOUNT_MISMATCH',
                        details={
                            'expected': expected_amount_toman,
                            'paid': paid_amount_toman,
                        },
                    )

                ref_number = data.get('refNumber', '')
                card_number = data.get('cardNumber', '')
                status = data.get('status', 0)
                paid_at = data.get('paidAt', '')
                message = cls.STATUS_MESSAGES.get(result_code, 'تراکنش موفق')

                logger.info(
                    f"Zibal payment verified: trackId={track_id}, "
                    f"refNumber={ref_number}, amount={paid_amount_toman}"
                )

                return {
                    'success': True,
                    'track_id': track_id,
                    'ref_number': ref_number,
                    'card_number': card_number,
                    'paid_amount': paid_amount_toman,
                    'status': status,
                    'paid_at': paid_at,
                    'message': message,
                }
            else:
                error_msg = cls.STATUS_MESSAGES.get(
                    result_code,
                    data.get('message', 'تراکنش ناموفق')
                )
                raise PaymentException(
                    message=error_msg,
                    code=f'ZIBAL_VERIFY_{result_code}',
                    details=data,
                )

        except requests.Timeout:
            raise PaymentException(
                message='زمان تایید تراکنش به پایان رسید',
                code='VERIFY_TIMEOUT',
            )
        except requests.RequestException as e:
            logger.error(f"Zibal verify error: {e}")
            raise PaymentException(
                message='خطا در تایید تراکنش',
                code='VERIFY_ERROR',
            )

    @classmethod
    def inquiry(cls, track_id: int) -> dict:
        """
        استعلام وضعیت تراکنش (بدون تایید)
        """
        merchant_id = cls._get_merchant_id()

        payload = {
            'merchant': merchant_id,
            'trackId': track_id,
        }

        try:
            response = requests.post(
                f'{cls.BASE_URL}/inquiry',
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Zibal inquiry error: {e}")
            return {'result': -1, 'message': str(e)}