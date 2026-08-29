"""
تنظیمات محیط توسعه (Development)
بیو کلاب — Local Development
"""

from .base import *  # noqa

# ─── Debug ───
DEBUG = True


IS_PRODUCTION = False
IS_DEVELOPMENT = True


# ─── Allowed Hosts ───
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '192.168.1.43',
]

# ─── CORS — باز برای توسعه ───
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ─── Database: PostgreSQL + PostGIS ───
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('DB_NAME', default='beau_dev'),
        'USER': env('DB_USER', default='beau_dev'),
        'PASSWORD': env('DB_PASSWORD', default='beau_dev_pass'),
        'HOST': env('DB_HOST', default='postgres'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# ─── Cache: Redis ───
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ─── Static & Media — Django serve in dev ───
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# ─── Email: Console (print to terminal) ───
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ─── SMS: Mock (no real SMS sent) ───
# KAVENEGAR_API_KEY is empty → MockSmsProvider will be used

# ─── Shahkar: Mock ───
# SHAHKAR_API_KEY is empty → MockNationalIdVerifier will be used

# ─── Payment: Sandbox ───
# ZARINPAL_SANDBOX=True → sandbox mode

# ─── Celery: Eager mode (optional — synchronous in dev) ───
# Set CELERY_TASK_ALWAYS_EAGER=True in .env if you want
# tasks to run synchronously without a worker
import os
if os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'False').lower() == 'true':
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# ─── Logging: Console with colors ───
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            'format': '{asctime} | {levelname:8s} | {name:30s} | {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname:8s} | {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Set to DEBUG to see SQL queries
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'shared': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# ─── Debug Toolbar (if installed) ───
try:
    import debug_toolbar  # noqa
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1', '0.0.0.0']
except ImportError:
    pass

# ─── Django Extensions (if installed) ───
try:
    import django_extensions  # noqa
    INSTALLED_APPS += ['django_extensions']
except ImportError:
    pass

# ─── Shell Plus (IPython) ───
SHELL_PLUS = "ipython"
SHELL_PLUS_PRINT_SQL = True

# ─── Media URL — served by Django in dev ───
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Static URL ───
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ─── Disable throttling in dev ───
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}