"""
SMS Service Factory
"""
from django.conf import settings


def get_sms_provider():
    """
    Factory برای دریافت provider پیامک بر اساس محیط
    - توسعه: MockSmsProvider
    - پروداکشن: KavenegarSmsProvider
    """
    if settings.DEBUG:
        from .mock import MockSmsProvider
        return MockSmsProvider()

    from .kavenegar import KavenegarSmsProvider
    return KavenegarSmsProvider(
        api_key=getattr(settings, 'KAVENEGAR_API_KEY', ''),
    )