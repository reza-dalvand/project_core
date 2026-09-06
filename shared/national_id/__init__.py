# shared/national_id/__init__.py
# جایگزین کامل فایل

"""
National ID Verifier Factory

✅ FIX: شرایط انتخاب:
- اگر DEBUG=True → ماک
- اگر SHAHAR_API_KEY فیک است → ماک (با هشدار)
- در غیر این صورت → سرویس واقعی
"""
from django.conf import settings


def get_national_id_verifier():
    """
    Factory برای دریافت verifier بر اساس محیط
    """
    api_key = getattr(settings, 'SHAHKAR_API_KEY', '')
    api_url = getattr(settings, 'SHAHKAR_API_URL', None)

    # ✅ FIX: اگر DEBUG=True یا کلید فیک باشد، ماک استفاده شود
    is_fake_key = (
        not api_key
        or api_key == 'fake-api-key-for-dev'
        or 'your-token' in api_key.lower()
    )

    if settings.DEBUG or is_fake_key:
        if is_fake_key:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                'SHAHKAR_API_KEY تنظیم نشده یا فیک است. '
                'از ماک استفاده می‌شود.'
            )
        from .mock import MockNationalIdVerifier
        return MockNationalIdVerifier()

    from .api_ir import ApiIrNationalIdVerifier
    return ApiIrNationalIdVerifier(
        api_key=api_key,
        api_url=api_url,
    )