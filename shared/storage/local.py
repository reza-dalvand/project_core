"""
Local Storage Backend برای محیط توسعه
ذخیره فایل‌ها در فیل سیستم محلی
"""
import logging
from django.core.files.storage import default_storage
from .base import AbstractStorageBackend, StorageResult

logger = logging.getLogger(__name__)


class LocalStorage(AbstractStorageBackend):
    """ذخیره‌ساز محلی برای توسعه"""

    def __init__(self):
        self._storage = default_storage

    def save(self, name: str, content) -> StorageResult:
        """ذخیره فایل در فیل سیستم محلی"""
        try:
            saved_name = self._storage.save(name, content)
            return StorageResult(
                success=True,
                file_url=self._storage.url(saved_name),
            )
        except Exception as e:
            logger.error(f"Local storage error: {e}")
            return StorageResult(
                success=False,
                error_message=str(e),
            )

    def url(self, name: str) -> str:
        """دریافت URL فایل"""
        return self._storage.url(name)

    def delete(self, name: str) -> bool:
        """حذف فایل"""
        try:
            self._storage.delete(name)
            return True
        except Exception as e:
            logger.error(f"Local delete error: {e}")
            return False

    def exists(self, name: str) -> bool:
        """بررسی وجود فایل"""
        return self._storage.exists(name)