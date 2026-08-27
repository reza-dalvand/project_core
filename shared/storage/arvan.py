"""
Arvan Cloud Storage Backend
مستندات: https://docs.arvancloud.ir/fa/products/cloud-storage

ابزارها:
- S3 API برای ذخیره‌سازی فایل‌ها
- CDN برای توزیع فایل‌های استاتیک و رسانه‌ای
"""
import logging
from typing import Optional
from django.conf import settings
from .base import AbstractStorageBackend, StorageResult

logger = logging.getLogger(__name__)


class ArvanCloudStorage(AbstractStorageBackend):
    """
    ذخیره‌سازی در ابر آروان با استفاده از S3 API
    """

    DEFAULT_ENDPOINT = 'https://s3.ir-thr-at1.arvanstorage.ir'
    DEFAULT_REGION = 'ir-thr-at1'

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        endpoint_url: str = None,
        region_name: str = None,
        cdn_url: str = '',
    ):
        if not access_key or not secret_key:
            raise ValueError(
                'ARVAN_ACCESS_KEY و ARVAN_SECRET_KEY تنظیم نشده‌اند'
            )
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket_name = bucket_name
        self._endpoint_url = endpoint_url or self.DEFAULT_ENDPOINT
        self._region_name = region_name or self.DEFAULT_REGION
        self._cdn_url = cdn_url
        self._client = None

    @property
    def client(self):
        """Lazy init برای S3 client"""
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config

                self._client = boto3.client(
                    's3',
                    endpoint_url=self._endpoint_url,
                    aws_access_key_id=self._access_key,
                    aws_secret_access_key=self._secret_key,
                    region_name=self._region_name,
                    config=Config(signature_version='s3v4'),
                )
            except ImportError:
                raise ImportError(
                    'پکیج boto3 نصب نیست. '
                    'نصب کنید: pip install boto3'
                )
        return self._client

    def save(self, name: str, content) -> StorageResult:
        """ذخیره فایل در باکت ابر آروان"""
        try:
            self.client.put_object(
                Bucket=self._bucket_name,
                Key=name,
                Body=content.read(),
                ContentType=getattr(
                    content, 'content_type', 'application/octet-stream'
                ),
            )
            return StorageResult(
                success=True,
                file_url=self.url(name),
            )
        except Exception as e:
            logger.error(f"Arvan Cloud storage error: {e}")
            return StorageResult(
                success=False,
                error_message=str(e),
            )

    def url(self, name: str) -> str:
        """دریافت URL فایل"""
        if self._cdn_url:
            return f'{self._cdn_url.rstrip("/")}/{name}'
        return f'{self._endpoint_url}/{self._bucket_name}/{name}'

    def delete(self, name: str) -> bool:
        """حذف فایل"""
        try:
            self.client.delete_object(
                Bucket=self._bucket_name,
                Key=name,
            )
            return True
        except Exception as e:
            logger.error(f"Arvan Cloud delete error: {e}")
            return False

    def exists(self, name: str) -> bool:
        """بررسی وجود فایل"""
        try:
            self.client.head_object(
                Bucket=self._bucket_name,
                Key=name,
            )
            return True
        except Exception:
            return False