"""
تنظیمات Celery برای بیو کلاب
"""
import os
from celery import Celery

# ✅ تغییر از development به production
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('BeauClub')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task برای دیباگ"""
    print(f'Request: {self.request!r}')