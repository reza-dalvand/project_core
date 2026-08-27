"""
Custom Storage Backends for Arvan Cloud S3
"""
from django.conf import settings

try:
    from storages.backends.s3boto3 import S3Boto3Storage
except ImportError:
    from django.core.files.storage import FileSystemStorage as S3Boto3Storage


class ArvanCloudStorage(S3Boto3Storage):
    pass


class BusinessImageStorage(ArvanCloudStorage):
    pass


class UserAvatarStorage(ArvanCloudStorage):
    pass


class PortfolioImageStorage(ArvanCloudStorage):
    pass


# ═══════════════════════════════════════════════
#   Factory Functions
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