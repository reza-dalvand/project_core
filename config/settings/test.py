"""
تنظیمات محیط تست
ارث‌بری از base با تنظیمات خاص تست
"""
from .base import *  # noqa

DEBUG = True

SECRET_KEY = 'test-secret-key-not-for-production-only'

# ─── Database: PostGIS (برای تست‌های GIS) ───
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('TEST_DB_NAME', default='test_beau'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default='postgres'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# ─── Cache: غیرفعال (بدون Redis) ───
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# ─── DRF: غیرفعال کردن throttling برای تست ───
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# ─── CORS: باز برای تست ───
CORS_ALLOW_ALL_ORIGINS = True

# ─── SMS: Mock (بدون API Key واقعی) ───
KAVENEGAR_API_KEY = ''

# ─── Shahkar: Mock ───
SHAHKAR_API_KEY = ''

# ─── Celery: اجرای همزمان (بدون worker) ───
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ─── Logging: حداقل ───
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}