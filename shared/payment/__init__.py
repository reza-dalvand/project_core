"""
Payment Gateway Factory
"""
from django.conf import settings


def get_payment_gateway():
    """
    Factory برای دریافت درگاه پرداخت بر اساس تنظیمات
    """
    merchant_id = getattr(settings, 'ZIBAL_MERCHANT_ID', '')

    from .zibal import ZibalGateway
    return ZibalGateway(merchant_id=merchant_id)