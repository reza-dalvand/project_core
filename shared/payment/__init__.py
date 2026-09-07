"""
Payment Gateway Factory
"""
from django.conf import settings


def get_payment_gateway():
    """
    Factory برای دریافت درگاه پرداخت بر اساس تنظیمات
    """
    merchant_id = getattr(
        settings, 'ZARINPAL_MERCHANT_ID', '11111111-1111-1111-1111-111111111111'
    )
    sandbox = getattr(settings, 'ZARINPAL_SANDBOX', True)

    from .zarinpal import ZarinPalGateway
    return ZarinPalGateway(merchant_id=merchant_id, sandbox=sandbox)