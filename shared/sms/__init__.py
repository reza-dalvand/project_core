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
    'test-fake-kavenegar-key',  # ✅ کلید محیط تست
}


def get_sms_provider():
    """
    Factory برای دریافت سرویس پیامک بر اساس متغیر گلوبال محیط

    منطق جدید:
    1. در محیط تست (APP_ENV=test) همیشه از Console Provider استفاده می‌شود
       تا پیامک واقعی ارسال نشود و هزینه کسر نگردد.
    2. در سایر محیط‌ها در صورت وجود کلید API معتبر، از Kavenegar واقعی استفاده می‌شود.
    3. در غیر این صورت از Console Provider استفاده می‌شود.
    """
    app_env = getattr(settings, 'APP_ENV', 'development').lower()
    
    # ✅ اولویت اول: محیط تست — همیشه Console
    if app_env == 'test':
        from .console import KavenegarConsoleSmsProvider
        logger.info('🧪 محیط تست: استفاده از Console SMS Provider')
        return KavenegarConsoleSmsProvider()

    from .kavenegar import KavenegarSmsProvider
    from .console import KavenegarConsoleSmsProvider

    api_key = getattr(settings, 'KAVENEGAR_API_KEY', '')

    # اولویت دوم: کلید معتبر = Kavenegar واقعی
    if api_key and api_key not in INVALID_API_KEYS and 'your-kavenegar-api-key' not in api_key:
        logger.info('📱 استفاده از Kavenegar SMS Provider (کلید معتبر)')
        return KavenegarSmsProvider(api_key=api_key)

    # فال‌بک: Console
    logger.warning(
        'KAVENEGAR_API_KEY تنظیم نشده یا معتبر نیست. از Console SMS Provider استفاده می‌شود.'
    )
    return KavenegarConsoleSmsProvider()