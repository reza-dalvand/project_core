"""
Abstract Storage Backend
الگوی Strategy Pattern برای ذخیره‌سازی فایل‌ها
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class StorageResult:
    """نتیجه عملیات ذخیره‌سازی"""
    success: bool
    file_url: str = ''
    error_message: str = ''


class AbstractStorageBackend(ABC):
    """
    کلاس پایه انتزاعی برای ذخیره‌ساز
    هر ذخیره‌ساز باید این کلاس را پیاده‌سازی کند
    """

    @abstractmethod
    def save(self, name: str, content) -> StorageResult:
        """ذخیره فایل"""
        ...

    @abstractmethod
    def url(self, name: str) -> str:
        """دریافت URL فایل"""
        ...

    @abstractmethod
    def delete(self, name: str) -> bool:
        """حذف فایل"""
        ...

    @abstractmethod
    def exists(self, name: str) -> bool:
        """بررسی وجود فایل"""
        ...