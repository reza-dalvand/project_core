"""
تنظیمات Celery برای بیو کلاب
"""
import os
from celery import Celery

# تنظیمات جنگو برای Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('BeauClub')

# خواندن تنظیمات از settings جنگو با پیشوند CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# کشف task ها در همه اپ‌ها
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task برای دیباگ"""
    print(f'Request: {self.request!r}')