"""
Arvan Cloud Storage Configuration
تنظیمات ابر آروان برای ذخیره‌سازی فایل‌ها
"""
from django.conf import settings


def get_storage_config() -> dict:
    """
    دریافت تنظیمات storage بر اساس محیط
    """
    if settings.DEBUG:
        return {
            'backend': 'django.core.files.storage.FileSystemStorage',
            'options': {},
        }

    access_key = getattr(settings, 'ARVAN_ACCESS_KEY', '')
    secret_key = getattr(settings, 'ARVAN_SECRET_KEY', '')

    if not access_key or not secret_key:
        return {
            'backend': 'django.core.files.storage.FileSystemStorage',
            'options': {},
        }

    bucket = getattr(settings, 'ARVAN_BUCKET_NAME', 'zibano')
    endpoint = getattr(
        settings, 'ARVAN_ENDPOINT',
        'https://s3.ir-thr-at1.arvanstorage.ir'
    )
    region = getattr(settings, 'ARVAN_REGION', 'ir-thr-at1')
    cdn_url = getattr(settings, 'ARVAN_CDN_URL', '')

    custom_domain = cdn_url if cdn_url else (
        f'{bucket}.{endpoint.replace("https://", "")}'
    )

    return {
        'backend': 'storages.backends.s3boto3.S3Boto3Storage',
        'options': {
            'access_key': access_key,
            'secret_key': secret_key,
            'bucket_name': bucket,
            'endpoint_url': endpoint,
            'region_name': region,
            'default_acl': 'public-read',
            'querystring_auth': False,
            'file_overwrite': False,
            'custom_domain': custom_domain,
        },
    }