"""
Storage Service Factory
"""
from django.conf import settings


def get_storage_backend():
    """
    Factory برای انتخاب ذخیره‌ساز بر اساس محیط
    - توسعه: LocalStorage
    - پروداکشن: ArvanCloudStorage (اگر مقادیر تنظیم شده باشد)
    """
    if settings.DEBUG:
        from .local import LocalStorage
        return LocalStorage()

    access_key = getattr(settings, 'ARVAN_ACCESS_KEY', '')
    secret_key = getattr(settings, 'ARVAN_SECRET_KEY', '')

    if not access_key or not secret_key:
        from .local import LocalStorage
        return LocalStorage()

    from .arvan import ArvanCloudStorage
    return ArvanCloudStorage(
        access_key=access_key,
        secret_key=secret_key,
        bucket_name=getattr(settings, 'ARVAN_BUCKET_NAME', 'beau'),
        endpoint_url=getattr(
            settings, 'ARVAN_ENDPOINT',
            'https://s3.ir-thr-at1.arvanstorage.ir',
        ),
        region_name=getattr(settings, 'ARVAN_REGION', 'ir-thr-at1'),
        cdn_url=getattr(settings, 'ARVAN_CDN_URL', ''),
    )