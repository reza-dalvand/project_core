"""
National ID Verifier Factory
"""
from django.conf import settings


def get_national_id_verifier():
    """
    Factory برای دریافت verifier بر اساس محیط
    - توسعه: MockNationalIdVerifier
    - پروداکشن: ApiIrNationalIdVerifier (Shahkar Lite)
    """
    if settings.DEBUG:
        from .mock import MockNationalIdVerifier
        return MockNationalIdVerifier()

    from .api_ir import ApiIrNationalIdVerifier
    return ApiIrNationalIdVerifier(
        api_key=getattr(settings, 'SHAHKAR_API_KEY', ''),
        api_url=getattr(settings, 'SHAHKAR_API_URL', None),
    )