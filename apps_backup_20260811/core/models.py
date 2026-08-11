"""
Base Model برای تمام مدل‌های زیبانو
"""
from django.db import models


class BaseModel(models.Model):
    """بیس‌مدل برای همه مدل‌ها"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True