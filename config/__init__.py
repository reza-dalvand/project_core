"""
Config package init
بارگذاری Celery app هنگام شروع جنگو
"""
from .celery import app as celery_app

__all__ = ('celery_app',)