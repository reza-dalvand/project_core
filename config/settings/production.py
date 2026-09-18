"""
تنظیمات محیط پروداکشن (Production)
بیو کلاب - نسخه نهایی سرور
"""
import os
from pathlib import Path
from .base import *  # noqa

DEBUG = False


# ─── App Environment ───
# APP_ENV از .env خوانده می‌شود تا به صورت گلوبال برای سرویس‌ها قابل استفاده باشد.
# نکته امنیتی: در محیط پروداکشن نباید کدهای پیامکی در کنسول/لاگ چاپ شوند.
APP_ENV = env('APP_ENV', default='production').lower()
IS_PRODUCTION = APP_ENV == 'production'
IS_DEVELOPMENT = APP_ENV == 'development'


# ─── Allowed Hosts ───
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[
    'beauclub.ir',
    'beuclub.ir',
    'buclub.ir',
    'api.beauclub.ir',
    'develop.beauclub.ir', 
    'app.beauclub.ir', 
    'localhost',
    '127.0.0.1',

])

###


# ─── CSRF Trusted Origins (Django 4+) ───
CSRF_TRUSTED_ORIGINS = [
    'https://beauclub.ir',
    'https://beuclub.ir',
    'https://buclub.ir',
    'https://api.beauclub.ir',
    'https://develop.beauclub.ir',
    'https://app.beauclub.ir', 
    'https://www.beauclub.ir',
    'https://www.beuclub.ir',
    'https://www.buclub.ir',
    env('FRONTEND_URL', default='https://app.beauclub.ir'),
    'capacitor://localhost',
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

# ─── Storage: S3 (Arvan Cloud) ───
_storage_access = env('ARVAN_ACCESS_KEY', default='')
_storage_secret = env('ARVAN_SECRET_KEY', default='')

if _storage_access and _storage_secret:
    ARVAN_BUCKET = env('ARVAN_BUCKET_NAME', default='beau')
    ARVAN_ENDPOINT = env('ARVAN_ENDPOINT', default='https://s3.ir-thr-at1.arvanstorage.ir')
    ARVAN_REGION = env('ARVAN_REGION', default='ir-thr-at1')
    ARVAN_CDN = env('ARVAN_CDN_URL', default='')

    # تنظیمات پایه S3
    s3_options = {
        "access_key": _storage_access,
        "secret_key": _storage_secret,
        "bucket_name": ARVAN_BUCKET,
        "endpoint_url": ARVAN_ENDPOINT,
        "region_name": ARVAN_REGION,
        "default_acl": "public-read",
        "querystring_auth": False,
        "url_protocol": "https:",  # ✅ تضمین استفاده از HTTPS برای لینک‌ها
    }
    if ARVAN_CDN:
        s3_options["custom_domain"] = ARVAN_CDN

    # ۱. Media Files (فایل‌های آپلودی کاربران مثل عکس پروفایل، گالری و ...)
    media_options = s3_options.copy()
    media_options["file_overwrite"] = False
    media_options["location"] = "media"  # ✅ تفکیک پوشه در باکت
    
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": media_options,
    }

    # ۲. Static Files (فایل‌های CSS, JS, فونت‌ها و ...)
    static_options = s3_options.copy()
    static_options["file_overwrite"] = True
    static_options["location"] = "static"  # ✅ تفکیک پوشه در باکت
    
    STORAGES["staticfiles"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": static_options,
    }

    # تنظیم URLهای پایه برای fallback
    if ARVAN_CDN:
        STATIC_URL = f'https://{ARVAN_CDN}/static/'
        MEDIA_URL = f'https://{ARVAN_CDN}/media/'

        
# ─── CORS — Production ───
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'https://beauclub.ir',
    'https://beuclub.ir',
    'https://buclub.ir',
    'https://api.beauclub.ir',
    'https://develop.beauclub.ir', 
    'https://app.beauclub.ir',
    'https://www.beauclub.ir',
    'https://www.beuclub.ir',
    'https://www.buclub.ir',
    env('FRONTEND_URL', default='https://app.beauclub.ir'),
    'capacitor://localhost',
]

# ═══ 🆕 فاز ۵: پشتیبان با Regex ═══
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^capacitor://localhost$',
    r'^https://beauclub\.ir$',
    r'^https://app\.beauclub\.ir$',
    r'^https://.*\.beauclub\.ir$',
    r'^https://www\.beauclub\.ir$',
    r'^https://beuclub\.ir$',
    r'^https://buclub\.ir$',
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'x-app-version', 'x-device-name', 'x-os-version',
]

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
        # 'file_app': {
        #     'level': 'INFO',
        #     'class': 'logging.handlers.RotatingFileHandler',
        #     'filename': str(LOG_DIR / 'app.log'),
        #     'maxBytes': 10 * 1024 * 1024,  # 10MB
        #     'backupCount': 5,
        #     'formatter': 'simple',
        # },
        # 'file_error': {
        #     'level': 'ERROR',
        #     'class': 'logging.handlers.RotatingFileHandler',
        #     'filename': str(LOG_DIR / 'error.log'),
        #     'maxBytes': 10 * 1024 * 1024,
        #     'backupCount': 10,
        #     'formatter': 'verbose',
        # },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

