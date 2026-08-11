"""
National ID Verifier Factory
"""
from django.conf import settings


def get_national_id_verifier():
    """
    Factory برای دریافت verifier بر اساس محیط
    """
    if settings.DEBUG:
        from .mock import MockNationalIdVerifier
        return MockNationalIdVerifier()

    from .api_ir import ApiIrNationalIdVerifier
    return ApiIrNationalIdVerifier(
        api_url=getattr(settings, 'SHAHKAR_API_URL', ''),
        api_key=getattr(settings, 'SHAHKAR_API_KEY', ''),
    )