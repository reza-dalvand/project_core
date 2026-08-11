# """
# Custom Storage Backends for Arvan Cloud S3
# """
# from django.conf import settings
# from storages.backends.s3boto3 import S3Boto3Storage
#
#
# class ArvanCloudStorage(S3Boto3Storage):
#     """
#     Storage backend برای Arvan Cloud Object Storage
#     سازگار با S3 API
#     """
#
#     def __init__(self, **settings_override):
#         # تنظیمات پیش‌فرض از settings
#         self.access_key = settings_override.get('access_key', getattr(settings, 'ARVAN_ACCESS_KEY', ''))
#         self.secret_key = settings_override.get('secret_key', getattr(settings, 'ARVAN_SECRET_KEY', ''))
#         self.bucket_name = settings_override.get('bucket_name', getattr(settings, 'ARVAN_BUCKET_NAME', 'zibano'))
#         self.endpoint_url = settings_override.get('endpoint_url', getattr(settings, 'ARVAN_ENDPOINT',
#                                                                           'https://s3.ir-thr-at1.arvanstorage.ir'))
#         self.region_name = settings_override.get('region_name', getattr(settings, 'ARVAN_REGION', 'ir-thr-at1'))
#         self.custom_domain = settings_override.get('custom_domain', getattr(settings, 'ARVAN_CDN_URL', ''))
#
#         # تنظیمات S3
#         self.default_acl = settings_override.get('default_acl', 'public-read')
#         self.querystring_auth = settings_override.get('querystring_auth', False)
#         self.file_overwrite = settings_override.get('file_overwrite', False)
#
#         super().__init__(**settings_override)
#
#
# class BusinessImageStorage(ArvanCloudStorage):
#     """
#     Storage مخصوص تصاویر کسب‌وکارها
#     مسیر: businesses/{business_id}/{filename}
#     """
#     location = 'businesses'
#     file_overwrite = False
#
#
# class UserAvatarStorage(ArvanCloudStorage):
#     """
#     Storage مخصوص آواتار کاربران
#     مسیر: avatars/{user_id}/{filename}
#     """
#     location = 'avatars'
#     file_overwrite = True
#
#
# class PortfolioImageStorage(ArvanCloudStorage):
#     """
#     Storage مخصوص تصاویر پورتفولیو
#     مسیر: portfolios/{business_id}/{portfolio_id}/{filename}
#     """
#     location = 'portfolios'
#     file_overwrite = False
#
#
# # Factory function برای استفاده در مدل‌ها
# def get_business_image_storage():
#     """Factory برای BusinessImageStorage"""
#     return BusinessImageStorage()
#
#
# def get_user_avatar_storage():
#     """Factory برای UserAvatarStorage"""
#     return UserAvatarStorage()
#
#
# def get_portfolio_image_storage():
#     """Factory برای PortfolioImageStorage"""
#     return PortfolioImageStorage()

#when on local
# apps/core/storage.py

"""
Custom Storage Backends for Arvan Cloud S3
"""
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class ArvanCloudStorage(S3Boto3Storage):
    # ... (کدهای قبلی بدون تغییر)
    pass


class BusinessImageStorage(ArvanCloudStorage):
    # ... (کدهای قبلی بدون تغییر)
    pass


class UserAvatarStorage(ArvanCloudStorage):
    # ... (کدهای قبلی بدون تغییر)
    pass


class PortfolioImageStorage(ArvanCloudStorage):
    # ... (کدهای قبلی بدون تغییر)
    pass


# ═══════════════════════════════════════════════
#   Factory Functions - اصلاح شده برای محیط توسعه
# ═══════════════════════════════════════════════

def get_business_image_storage():
    """Factory برای BusinessImageStorage"""
    if getattr(settings, 'DEBUG', False):
        from django.core.files.storage import default_storage
        return default_storage
    return BusinessImageStorage()


def get_user_avatar_storage():
    """Factory برای UserAvatarStorage"""
    if getattr(settings, 'DEBUG', False):
        from django.core.files.storage import default_storage
        return default_storage
    return UserAvatarStorage()


def get_portfolio_image_storage():
    """Factory برای PortfolioImageStorage"""
    if getattr(settings, 'DEBUG', False):
        from django.core.files.storage import default_storage
        return default_storage
    return PortfolioImageStorage()