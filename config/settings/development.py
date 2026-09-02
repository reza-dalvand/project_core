"""
تنظیمات محیط توسعه (Development)
بیو کلاب — Local Development

✅ اصل مهم این فایل:
در محیط توسعه، استاتیک‌ها و مدیا همیشه لوکال سرو می‌شوند
و هرگز از آروان (Arvan Cloud) خوانده نمی‌شوند — حتی اگر
فایل .env شامل کلیدهای واقعی آروان یا APP_ENV=production باشد.
"""
from .base import *  # noqa

# ─── Debug ───
DEBUG = True

# ─── App Environment: همیشه development در دولوپمنت ───
# حتی اگر .env مقدار production داشته باشد، اینجا خنثی می‌شود.
APP_ENV = 'development'
IS_PRODUCTION = False
IS_DEVELOPMENT = True

# ─── غیرفعال‌سازی کامل آروان در توسعه ───
# با خالی کردن کلیدها، هیچ‌کدام از factory ها (storage/sms/payment)
# در این محیط به سرویس خارجی وصل نمی‌شوند.
ARVAN_ACCESS_KEY = ''
ARVAN_SECRET_KEY = ''
ARVAN_CDN_URL = ''

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

# ═══════════════════════════════════════════════
#   Storage: ۱۰۰٪ لوکال — هرگز از آروان نخوان
# ═══════════════════════════════════════════════
STORAGES = {
    "default": {
        # فایل‌های آپلودی (media) روی دیسک محلی
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # ✅ StaticFilesStorage یعنی سرو استاتیک با STATIC_URL
        # از طریق staticfiles finders — بدون manifest و بدون S3.
        # (FileSystemStorageِ خام اینجا غلط بود چون base_url ندارد)
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ─── سرو استاتیک توسط خود Django در توسعه ───
# WhiteNoise فقط برای پروداکشن لازم است؛ در دولوپمنت حذفش می‌کنیم
# تا runserver مستقیماً /static/ را سرو کند و نیازی به collectstatic نباشد.
MIDDLEWARE = [
    m for m in MIDDLEWARE
    if m != 'whitenoise.middleware.WhiteNoiseMiddleware'
]

# ─── Static & Media — لوکال ───
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Email: Console (print to terminal) ───
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ─── SMS: Console (بدون ارسال واقعی) ───
# ─── Shahkar: Mock ───
# ─── Payment: Sandbox ───

# ─── Celery: Eager mode (optional — synchronous in dev) ───
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
            'level': 'WARNING',
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

# ─── Disable throttling in dev ───
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}