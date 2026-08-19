"""
Custom Exception Handler for DRF
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """هندلر سفارشی برای تمام exceptions"""
    response = exception_handler(exc, context)
    view = context.get('view', None)
    view_name = view.__class__.__name__ if view else 'Unknown'

    error_response = {
        'success': False,
        'error': {
            'code': 'UNKNOWN_ERROR',
            'message': 'خطای ناشناخته‌ای رخ داد',
            'details': {},
        }
    }

    if isinstance(exc, DjangoValidationError):
        error_response['error']['code'] = 'VALIDATION_ERROR'
        error_response['error']['message'] = 'داده‌های ورودی معتبر نیست'
        error_response['error']['details'] = (
            exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}
        )
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, Http404):
        error_response['error']['code'] = 'NOT_FOUND'
        error_response['error']['message'] = 'منبع مورد نظر یافت نشد'
        return Response(error_response, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, PermissionDenied):
        error_response['error']['code'] = 'PERMISSION_DENIED'
        error_response['error']['message'] = str(exc) or 'شما دسترسی لازم را ندارید'
        return Response(error_response, status=status.HTTP_403_FORBIDDEN)

    if response is not None:
        error_code_map = {
            400: 'BAD_REQUEST',
            401: 'UNAUTHORIZED',
            403: 'FORBIDDEN',
            404: 'NOT_FOUND',
            405: 'METHOD_NOT_ALLOWED',
            429: 'TOO_MANY_REQUESTS',
            500: 'SERVER_ERROR',
        }
        error_response['error']['code'] = error_code_map.get(
            response.status_code, 'ERROR'
        )

        if isinstance(response.data, dict):
            if 'detail' in response.data:
                error_response['error']['message'] = str(response.data['detail'])
            else:
                error_response['error']['details'] = response.data
                error_response['error']['message'] = 'خطای اعتبارسنجی'
        elif isinstance(response.data, list):
            error_response['error']['details'] = {'errors': response.data}
            error_response['error']['message'] = response.data[0] if response.data else 'خطا'
        else:
            error_response['error']['message'] = str(response.data)

        if response.status_code == 401:
            error_response['error']['message'] = 'احراز هویت ناموفق. لطفاً وارد شوید'
        elif response.status_code == 429:
            error_response['error']['message'] = 'تعداد درخواست‌ها بیش از حد مجاز است'

        response.data = error_response
        return response

    logger.exception(f"Unhandled exception in {view_name}: {exc}")
    error_response['error']['code'] = 'INTERNAL_SERVER_ERROR'
    error_response['error']['message'] = 'خطای داخلی سرور. لطفاً بعداً تلاش کنید'
    return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ═══════════════════════════════════════════════
#   Custom Exceptions
# ═══════════════════════════════════════════════

class BeauClubBaseException(Exception):
    """Base exception"""
    default_message = 'خطایی رخ داده است'
    default_code = 'BEAU_CLUB_ERROR'
    default_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, message=None, code=None, details=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details or {}
        super().__init__(self.message)

    def as_response(self):
        return Response(
            {
                'success': False,
                'error': {
                    'code': self.code,
                    'message': self.message,
                    'details': self.details,
                }
            },
            status=self.default_status,
        )


class OTPException(BeauClubBaseException):
    default_message = 'خطا در ارسال کد تایید'
    default_code = 'OTP_ERROR'


class OTPExpiredException(OTPException):
    default_message = 'کد تایید منقضی شده است'
    default_code = 'OTP_EXPIRED'


class OTPInvalidException(OTPException):
    default_message = 'کد تایید وارد شده صحیح نیست'
    default_code = 'OTP_INVALID'


class OTPTooManyAttemptsException(OTPException):
    default_message = 'تعداد تلاش‌ها بیش از حد مجاز است'
    default_code = 'OTP_TOO_MANY_ATTEMPTS'


class OTPRateLimitException(OTPException):
    default_message = 'لطفاً کمی صبر کنید و دوباره تلاش کنید'
    default_code = 'OTP_RATE_LIMIT'


class ShahkarException(BeauClubBaseException):
    default_message = 'خطا در استعلام کد ملی'
    default_code = 'SHAHKAR_ERROR'


class ShahkarMismatchException(ShahkarException):
    default_message = 'کد ملی با شماره موبایل مطابقت ندارد'
    default_code = 'SHAHKAR_MISMATCH'


class PaymentException(BeauClubBaseException):
    default_message = 'خطا در پرداخت'
    default_code = 'PAYMENT_ERROR'


class InsufficientBalanceException(BeauClubBaseException):
    default_message = 'موجودی کافی نیست'
    default_code = 'INSUFFICIENT_BALANCE'


class BookingException(BeauClubBaseException):
    default_message = 'خطا در رزرو نوبت'
    default_code = 'BOOKING_ERROR'


class SlotNotAvailableException(BookingException):
    default_message = 'این ساعت دیگر آزاد نیست'
    default_code = 'SLOT_NOT_AVAILABLE'


class ReviewException(BeauClubBaseException):
    default_message = 'خطا در ثبت نظر'
    default_code = 'REVIEW_ERROR'


class ReviewAlreadyExistsException(ReviewException):
    default_message = 'شما قبلاً برای این نوبت نظر ثبت کرده‌اید'
    default_code = 'REVIEW_ALREADY_EXISTS'


class AppointmentNotCompletedException(ReviewException):
    default_message = 'فقط برای نوبت‌های انجام‌شده می‌توانید نظر ثبت کنید'
    default_code = 'APPOINTMENT_NOT_COMPLETED'