"""
تنظیمات محیط توسعه (Development)
"""
from .base import *  # noqa

DEBUG = True

# ─── Database: PostgreSQL + PostGIS ───
# در توسعه هم از PostGIS استفاده می‌کنیم
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('DB_NAME', default='zibano'),
        'USER': env('DB_USER', default='zibano'),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# ─── Cache: حافظه محلی ───
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# ─── Email Console ───
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ─── Static files ───
STORAGES["staticfiles"]["BACKEND"] = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
)

# ─── CORS: همه مجاز ───
CORS_ALLOW_ALL_ORIGINS = True

# ─── Celery: اجرای همزمان ───
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ─── Jazzmin UI Builder ───
JAZZMIN_SETTINGS['show_ui_builder'] = True

# ─── غیرفعال کردن Throttle در توسعه ───
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# ─── Storage: فایل سیستم محلی ───
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

# ─── غیرفعال کردن S3 در توسعه ───
ARVAN_ACCESS_KEY = ''
ARVAN_SECRET_KEY = ''

# ─── Debug Toolbar ───
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass