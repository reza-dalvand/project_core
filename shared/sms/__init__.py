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
    Factory برای دریافت سرویس پیامک
    
    منطق جدید:
    در تمام محیط‌ها در صورت وجود کلید API معتبر، از سرویس واقعی کاوه‌نگار استفاده می‌شود.
    در غیر این صورت (مثلاً محیط تست یا نبود کلید)، از Console Provider استفاده می‌شود.
    """
    from .kavenegar import KavenegarSmsProvider
    from .console import KavenegarConsoleSmsProvider

    api_key = getattr(settings, 'KAVENEGAR_API_KEY', '')

    # استفاده از کاوه‌نگار واقعی در تمام محیط‌ها به شرط معتبر بودن کلید
    if api_key and api_key not in INVALID_API_KEYS and 'your-kavenegar-api-key' not in api_key:
        return KavenegarSmsProvider(api_key=api_key)

    # فال‌بک به کنسول در صورت نبود کلید معتبر (مثل محیط تست)
    logger.warning(
        'KAVENEGAR_API_KEY تنظیم نشده یا معتبر نیست. از Console SMS Provider استفاده می‌شود.'
    )
    return KavenegarConsoleSmsProvider()