# config/celery.py
"""
تنظیمات Celery برای بیو کلاب
"""
import os
from celery import Celery


def _get_settings_module():
    """
    انتخاب ماژول تنظیمات بر اساس محیط اجرا:

    اولویت:
      1. متغیر محیطی DJANGO_SETTINGS_MODULE (اگر دستی ست شده باشد)
      2. متغیر محیطی DJANGO_ENV → production / development
      3. پیش‌فرض: development
    """
    explicit = os.environ.get('DJANGO_SETTINGS_MODULE')
    if explicit:
        return explicit

    env = os.environ.get('DJANGO_ENV', 'development').lower()

    if env == 'production':
        return 'config.settings.production'

    return 'config.settings.development'


os.environ.setdefault('DJANGO_SETTINGS_MODULE', _get_settings_module())

app = Celery('BeauClub')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task برای دیباگ"""
    print(f'Request: {self.request!r}')