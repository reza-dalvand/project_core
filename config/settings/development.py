"""
تنظیمات محیط توسعه (Development)
"""
from .base import *  # noqa

DEBUG = True

# Database: SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Cache: حافظه محلی
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Email Console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Static files
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"

# CORS: همه مجاز
CORS_ALLOW_ALL_ORIGINS = True

# Celery: اجرای همزمان
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ✅ اصلاح شده: Jazzmin UI Builder برای توسعه
JAZZMIN_SETTINGS['show_ui_builder'] = True

REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# ═══════════════════════════════════════════════
#   Storage: در محیط توسعه از فایل سیستم محلی استفاده کن
# ═══════════════════════════════════════════════
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": BASE_DIR / "media",
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Override کردن storage های سفارشی برای تست
# تا از S3 استفاده نکنند
ARVAN_ACCESS_KEY = ''
ARVAN_SECRET_KEY = ''