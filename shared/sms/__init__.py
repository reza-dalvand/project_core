"""
SMS Service Factory

انتخاب provider پیامک بر اساس متغیر گلوبال محیط:
- در محیط توسعه/تست: پیامک در کنسول چاپ می‌شود.
- در محیط پروداکشن: پیامک از طریق API کاوه‌نگار ارسال می‌شود.
"""
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

INVALID_API_KEYS = {
    '',
    'fake-api-key-for-dev',
    'your-kavenegar-api-key-here',
}


def get_sms_provider():
    """
    Factory برای دریافت سرویس پیامک بر اساس متغیر گلوبال محیط

    در محیط توسعه/تست:
        KavenegarConsoleSmsProvider
        رفتار کاوه‌نگار را شبیه‌سازی می‌کند اما ارسال واقعی انجام نمی‌دهد.
        پیام‌ها فقط در کنسول/لاگ چاپ می‌شوند.

    در محیط پروداکشن:
        KavenegarSmsProvider
        ارسال واقعی از طریق API کاوه‌نگار انجام می‌شود.
    """
    app_env = getattr(settings, 'APP_ENV', 'development').lower()
    is_production = getattr(settings, 'IS_PRODUCTION', False)
    debug = getattr(settings, 'DEBUG', False)

    if is_production:
        from .kavenegar import KavenegarSmsProvider

        api_key = getattr(settings, 'KAVENEGAR_API_KEY', '')

        if api_key in INVALID_API_KEYS or 'your-kavenegar-api-key' in api_key:
            logger.critical(
                'KAVENEGAR_API_KEY برای محیط پروداکشن تنظیم نشده است.'
            )
            raise ImproperlyConfigured(
                'KAVENEGAR_API_KEY برای محیط پروداکشن تنظیم نشده است.'
            )

        return KavenegarSmsProvider(api_key=api_key)

    if debug or app_env in {'development', 'test'}:
        from .console import KavenegarConsoleSmsProvider
        return KavenegarConsoleSmsProvider()

    # اگر تنظیمات پروداکشن باشد ولی APP_ENV=production نباشد،
    # پیامک را در کنسول چاپ نمی‌کنیم تا کدها در لاگ پروداکشن نشت نکنند.
    logger.critical(
        'APP_ENV برای ارسال پیامک در محیط غیرتوسعه باید برابر production باشد.'
    )
    raise ImproperlyConfigured(
        'APP_ENV برای ارسال پیامک در محیط غیرتوسعه باید برابر production باشد.'
    )