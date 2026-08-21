"""
تنظیمات محیط پروداکشن (Production)
بیو کلاب - نسخه نهایی سرور
"""
import os
from pathlib import Path
from .base import *  # noqa

DEBUG = False

# ─── Allowed Hosts ───
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[
    'beauclub.ir',
    'beuclub.ir',
    'buclub.ir',
    'api.beauclub.ir',
    'localhost',
    '127.0.0.1',
])

# ─── CSRF Trusted Origins (Django 4+) ───
CSRF_TRUSTED_ORIGINS = [
    'https://beauclub.ir',
    'https://beuclub.ir',
    'https://buclub.ir',
    'https://api.beauclub.ir',
    'https://www.beauclub.ir',
    'https://www.beuclub.ir',
    'https://www.buclub.ir',
    env('FRONTEND_URL', default='https://beauclub.ir'),
]

# ─── Security Headers ───
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ─── SSL / HSTS ───
# ✅ چون Nginx خودش HTTP→HTTPS redirect می‌کند،
# در Django این را False می‌گذاریم تا redirect loop ایجاد نشود
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ─── Database: PostgreSQL + PostGIS ───
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('DB_NAME', default='beau'),
        'USER': env('DB_USER', default='beau'),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST': env('DB_HOST', default='postgres'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# ─── Redis Cache ───
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ─── Static Files ───
# ✅ در Django 5.1 فقط STORAGES معتبر است، STATICFILES_STORAGE حذف شده
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ─── Media Files ───
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# ─── Email: فعلاً غیرفعال (فقط SMS استفاده می‌شود) ───
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ─── Sentry: فقط اگر DSN تنظیم شده باشد ───
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )

# ─── Storage: فایل سیستم محلی (Arvan S3 فعلاً فعال نیست) ───
# ✅ اگر Arvan S3 فعال شد، مقادیر ARVAN_ACCESS_KEY و ARVAN_SECRET_KEY را در .env تنظیم کنید
# در غیر این صورت فایل‌ها روی دیسک سرور ذخیره می‌شوند
_storage_access = env('ARVAN_ACCESS_KEY', default='')
_storage_secret = env('ARVAN_SECRET_KEY', default='')
if _storage_access and _storage_secret:
    from shared.storage.arvan import get_storage_config
    _storage_config = get_storage_config()
    STORAGES["default"] = {
        "BACKEND": _storage_config['backend'],
        "OPTIONS": _storage_config['options'],
    }

# ─── CORS — Production ───
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'https://beauclub.ir',
    'https://beuclub.ir',
    'https://buclub.ir',
    'https://api.beauclub.ir',
    'https://www.beauclub.ir',
    'https://www.beuclub.ir',
    'https://www.buclub.ir',
    env('FRONTEND_URL', default='https://beauclub.ir'),
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'x-app-version', 'x-device-name', 'x-os-version',
]

# ─── SMS: فعلاً Mock (Kavenegar API Key هنوز نیست) ───
# ✅ وقتی API Key گرفتید، فقط KAVENEGAR_API_KEY را در .env تنظیم کنید
# و در shared/sms/__init__.py منطق Mock را حذف کنید

# ─── Logging به فایل ───
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file_app': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'app.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'simple',
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'error.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file_app', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file_error'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['file_app', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file_app', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}