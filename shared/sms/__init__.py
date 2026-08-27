"""
SMS Service Factory
"""
from django.conf import settings

def get_sms_provider():
    """
    Factory برای دریافت provider پیامک بر اساس محیط
    - توسعه یا بدون کلید: MockSmsProvider
    - پروداکشن با کلید: KavenegarSmsProvider
    """
    if settings.DEBUG or not getattr(settings, 'KAVENEGAR_API_KEY', ''):
        from .mock import MockSmsProvider
        return MockSmsProvider()

    from .kavenegar import KavenegarSmsProvider
    return KavenegarSmsProvider(
        api_key=settings.KAVENEGAR_API_KEY,
    )