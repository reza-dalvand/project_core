# config/settings/test.py

"""
تنظیمات محیط تست
"""
from .base import *  # noqa

DEBUG = True
SECRET_KEY = 'test-secret-key-not-for-production-only'

# ─── Database ───
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('TEST_DB_NAME', default='test_beau'),
        'USER': env('TEST_DB_USER', default='postgres'),
        'PASSWORD': env('TEST_DB_PASSWORD', default='postgres'),
        'HOST': 'localhost',
        'PORT': '5432',
        'TEST': {
            'NAME': env('TEST_DB_NAME', default='test_beau'),
        },
    }
}

# ─── Cache ───
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# ─── DRF ───
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# ─── CORS ───
CORS_ALLOW_ALL_ORIGINS = True

# ─── SMS: Mock (بدون API Key واقعی) ───
KAVENEGAR_API_KEY = 'test-fake-kavenegar-key'

# ─── Shahkar: Mock ───
SHAHKAR_API_KEY = 'test-fake-shahkar-key'

# ─── Celery ───
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ─── Logging ───
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

# ═══════════════════════════════════════════════════════════
#   ✅ FIX: در محیط تست از StaticFilesStorage ساده استفاده کن
#   تا نیازی به فایل manifest (collectstatic) نباشد
# ═══════════════════════════════════════════════════════════
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}