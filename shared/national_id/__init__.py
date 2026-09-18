# shared/national_id/__init__.py
"""
National ID Verifier Factory
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def get_national_id_verifier():
    """
    Factory برای دریافت verifier.
    استراتژی: همیشه از API واقعی استفاده می‌کند.
    """
    api_key = getattr(settings, 'SHAHKAR_API_KEY', '')
    api_url = getattr(settings, 'SHAHKAR_API_URL', None)

    # بررسی وجود توکن واقعی
    is_invalid_key = (
        not api_key or 
        'your-shahkar-api-token' in api_key or 
        'fake' in api_key.lower() or
        'test' in api_key.lower()
    )

    if is_invalid_key:
        logger.error("❌ SHAHKAR_API_KEY is missing or invalid in settings.")
        raise ValueError(
            "سرویس استعلام کد ملی در دسترس نیست. "
            "لطفاً توکن معتبر SHAHKAR_API_KEY را در فایل .env تنظیم کنید."
        )

    # بازگرداندن سرویس واقعی
    from .api_ir import ApiIrNationalIdVerifier
    return ApiIrNationalIdVerifier(api_key=api_key, api_url=api_url)