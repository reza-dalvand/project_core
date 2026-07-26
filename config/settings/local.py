"""
تنظیمات محیط توسعه (Development)
"""
from .base import *  # noqa

DEBUG = True

# Database: SQLite برای توسعه
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

# Email Console Backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Debug Toolbar (در صورت نیاز)
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']

# Static files
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# CORS: همه مجاز در توسعه
CORS_ALLOW_ALL_ORIGINS = True

# Celery: اجرای همزمان (بدون worker)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Jazzmin UI Tweaks برای توسعه
JAZZMIN_SETTINGS['show_ui_builder'] = True  # noqa