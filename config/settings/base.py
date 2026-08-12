"""
Django Base Settings - تنظیمات مشترک برای تمام محیط‌ها
زیبانو - بک‌اند
"""
import os
import environ
from pathlib import Path
from datetime import timedelta

# ─── Base Directory ───
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Environment Variables ───
env = environ.Env(
    DEBUG=(bool, False),
)
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# ═══════════════════════════════════════════════
#   Core Settings
# ═══════════════════════════════════════════════
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me')
DEBUG = env('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
SITE_NAME = env('SITE_NAME', default='زیبانو')
SITE_DOMAIN = env('SITE_DOMAIN', default='http://localhost:8000')

# ═══════════════════════════════════════════════
#   Application Definition
# ═══════════════════════════════════════════════
THIRD_PARTY_APPS = [
    # ═══ Jazzmin باید اول از همه باشد ═══
    'jazzmin',

    # REST API
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'django_filters',
    'corsheaders',

    # Utils
    'django_cleanup.apps.CleanupConfig',
    'django_ckeditor_5',
    'import_export',
    'django_celery_beat',
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # ✅ GIS - PostGIS
    'django.contrib.gis',
]

LOCAL_APPS = [
    # Core
    'apps.core.apps.CoreConfig',

    # Auth
    'apps.accounts.apps.AccountsConfig',

    # Lookup Data
    'apps.categories.apps.CategoriesConfig',
    'apps.locations.apps.LocationsConfig',

    # Business
    'apps.businesses.apps.BusinessesConfig',
    'apps.services.apps.ServicesConfig',
    'apps.schedules.apps.SchedulesConfig',
    'apps.appointments.apps.AppointmentsConfig',

    # Financial
    'apps.payments.apps.PaymentsConfig',

    # Social
    'apps.reviews.apps.ReviewsConfig',
    'apps.portfolios.apps.PortfoliosConfig',
    'apps.explore.apps.ExploreConfig',

    # Ads
    'apps.ads.apps.AdsConfig',
    'apps.ads_management.apps.AdsManagementConfig',

    # Features
    'apps.reminders.apps.RemindersConfig',
    'apps.favorites.apps.FavoritesConfig',
    'apps.search.apps.SearchConfig',
    'apps.support.apps.SupportConfig',

    # System
    'apps.notifications.apps.NotificationsConfig',
    'apps.landing.apps.LandingConfig',
    'apps.dashboard.apps.DashboardConfig',
]

INSTALLED_APPS = THIRD_PARTY_APPS + DJANGO_APPS + LOCAL_APPS

# ═══════════════════════════════════════════════
#   Middleware
# ═══════════════════════════════════════════════
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ اضافه شد
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ═══════════════════════════════════════════════
#   Templates (Jinja2 + Django)
# ═══════════════════════════════════════════════
TEMPLATES = [
    {
        'BACKEND': 'django_jinja.jinja2.Jinja2',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'config.jinja2_env.environment',
            'match_extension': '.html',
            'match_regex': r'^(?!admin/|jazzmin/|rest_framework/|debug_toolbar/|import_export/|ckeditor/).*\.html$',
            'app_dirname': 'templates',
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.landing.context_processors.site_settings',
                'apps.landing.context_processors.all_sections',
            ],
            'extensions': [
                'jinja2.ext.do',
                'jinja2.ext.loopcontrols',
                'jinja2.ext.i18n',
                'django_jinja.builtins.extensions.CsrfExtension',
                'django_jinja.builtins.extensions.CacheExtension',
                'django_jinja.builtins.extensions.TimezoneExtension',
                'django_jinja.builtins.extensions.UrlsExtension',
                'django_jinja.builtins.extensions.StaticFilesExtension',
                'django_jinja.builtins.extensions.DjangoFiltersExtension',
            ],
            'bytecode_cache': {
                'name': 'default',
                'backend': 'django_jinja.cache.BytecodeCache',
                'enabled': False,
            },
            'autoescape': True,
            'auto_reload': DEBUG,
            'translation_engine': 'django.utils.translation',
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.landing.context_processors.site_settings',
                'apps.landing.context_processors.all_sections',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ═══════════════════════════════════════════════
#   Database (PostgreSQL + PostGIS)
# ═══════════════════════════════════════════════
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

# GDAL/GEOS Library Paths (اختیاری - اگر در مسیر پیش‌فرض نباشند)
# GDAL_LIBRARY_PATH = env('GDAL_LIBRARY_PATH', default='')
# GEOS_LIBRARY_PATH = env('GEOS_LIBRARY_PATH', default='')

# ═══════════════════════════════════════════════
#   Custom User Model
# ═══════════════════════════════════════════════
AUTH_USER_MODEL = 'accounts.User'

# ═══════════════════════════════════════════════
#   Password Validation
# ═══════════════════════════════════════════════
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ═══════════════════════════════════════════════
#   Internationalization
# ═══════════════════════════════════════════════
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# ═══════════════════════════════════════════════
#   Static & Media Files
# ═══════════════════════════════════════════════
STATIC_URL = env('STATIC_URL', default='/static/')
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = env('MEDIA_URL', default='/media/')
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ═══════════════════════════════════════════════
#   REST Framework
# ═══════════════════════════════════════════════
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}

# ═══════════════════════════════════════════════
#   JWT Settings
# ═══════════════════════════════════════════════
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# ═══════════════════════════════════════════════
#   External Services
# ═══════════════════════════════════════════════
# SMS
KAVENEGAR_API_KEY = env('KAVENEGAR_API_KEY', default='')

# National ID
SHAHKAR_API_URL = env('SHAHKAR_API_URL', default='')
SHAHKAR_API_KEY = env('SHAHKAR_API_KEY', default='')

# Payment
ZIBAL_MERCHANT_ID = env('ZIBAL_MERCHANT_ID', default='zibal')
ZIBAL_CALLBACK_URL = env(
    'ZIBAL_CALLBACK_URL',
    default='http://localhost:8000/api/v1/payments/callback/',
)

# ─── Frontend (PWA) ───
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')

# Storage (Arvan Cloud S3)
ARVAN_ACCESS_KEY = env('ARVAN_ACCESS_KEY', default='')
ARVAN_SECRET_KEY = env('ARVAN_SECRET_KEY', default='')
ARVAN_BUCKET_NAME = env('ARVAN_BUCKET_NAME', default='zibano')
ARVAN_ENDPOINT = env(
    'ARVAN_ENDPOINT',
    default='https://s3.ir-thr-at1.arvanstorage.ir',
)
ARVAN_REGION = env('ARVAN_REGION', default='ir-thr-at1')
ARVAN_CDN_URL = env('ARVAN_CDN_URL', default='')

# File Upload
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# ═══════════════════════════════════════════════
#   DRF Spectacular
# ═══════════════════════════════════════════════
SPECTACULAR_SETTINGS = {
    'TITLE': f'{SITE_NAME} API',
    'DESCRIPTION': 'API اپلیکیشن رزرو آنلاین خدمات زیبایی',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ═══════════════════════════════════════════════
#   CORS
# ═══════════════════════════════════════════════
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://localhost:3000',
        'http://localhost:8081',
        'http://127.0.0.1:3000',
    ]
)
CORS_ALLOW_CREDENTIALS = True

# ═══════════════════════════════════════════════
#   Redis Cache
# ═══════════════════════════════════════════════
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# ═══════════════════════════════════════════════
#   Celery
# ═══════════════════════════════════════════════
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ═══════════════════════════════════════════════
#   CKEditor 5
# ═══════════════════════════════════════════════
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Styles', 'Format', 'Bold', 'Italic', 'Underline', 'Strike'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent'],
            ['Link', 'Unlink', 'Anchor'],
            ['Image', 'Table', 'HorizontalRule', 'SpecialChar'],
            ['Source', '-', 'Maximize'],
        ],
        'height': 300,
        'width': '100%',
    },
}

# ═══════════════════════════════════════════════
#   Admin URLs
# ═══════════════════════════════════════════════
LANDING_ADMIN_URL = env('LANDING_ADMIN_URL', default='admin/')
APP_ADMIN_URL = env('APP_ADMIN_URL', default='app-admin/')
DASHBOARD_ADMIN_URL = env('DASHBOARD_ADMIN_URL', default='dashboard-admin/')
LOGIN_URL = f'/{LANDING_ADMIN_URL}login/'
LOGIN_REDIRECT_URL = f'/{LANDING_ADMIN_URL}'

# ═══════════════════════════════════════════════
#   Jazzmin Settings
# ═══════════════════════════════════════════════
JAZZMIN_SETTINGS = {
    "site_title": "زیبانو | پنل مدیریت",
    "site_header": "زیبانو",
    "site_brand": "Zibano Admin",
    "welcome_sign": "به پنل مدیریت زیبانو خوش آمدید",
    "copyright": "Zibano Co. © 2024-2026",
    "user_avatar": "avatar",
    "topmenu_links": [
        {"name": "🏠 سایت معرفی", "url": "/", "new_window": True},
        {"name": "📚 مستندات API", "url": "/api/docs/", "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "accounts": "fas fa-user-shield",
        "accounts.CustomUser": "fas fa-users",
        "accounts.OtpCode": "fas fa-key",
        "accounts.UserDevice": "fas fa-mobile-alt",
        "categories": "fas fa-layer-group",
        "categories.ServiceCategory": "fas fa-spa",
        "categories.SubService": "fas fa-list",
        "categories.BusinessCategory": "fas fa-store",
        "locations": "fas fa-map-marked-alt",
        "locations.Province": "fas fa-map",
        "locations.City": "fas fa-city",
        "businesses": "fas fa-building",
        "businesses.Business": "fas fa-building",
        "businesses.BusinessGallery": "fas fa-images",
        "businesses.BusinessTeamMember": "fas fa-users",
        "services": "fas fa-concierge-bell",
        "services.Service": "fas fa-concierge-bell",
        "schedules": "fas fa-calendar-week",
        "schedules.ServiceSchedule": "fas fa-calendar-day",
        "appointments": "fas fa-calendar-check",
        "appointments.Appointment": "fas fa-calendar-alt",
        "payments": "fas fa-credit-card",
        "payments.Transaction": "fas fa-receipt",
        "payments.Settlement": "fas fa-money-check-alt",
        "reviews": "fas fa-star",
        "reviews.Review": "fas fa-comment-alt",
        "portfolios": "fas fa-images",
        "portfolios.Portfolio": "fas fa-images",
        "ads": "fas fa-bullhorn",
        "ads.ModelRequest": "fas fa-user-tie",
        "ads.LineRental": "fas fa-handshake",
        "explore": "fas fa-compass",
        "explore.ExplorePost": "fas fa-image",
        "reminders": "fas fa-bell",
        "reminders.RenewalReminder": "fas fa-bell",
        "favorites": "fas fa-heart",
        "search": "fas fa-search",
        "support": "fas fa-headset",
        "notifications": "fas fa-bell",
        "landing": "fas fa-globe",
    },
    "show_ui_builder": False,
    "changeform_format": "collapsible",
    "order_with_respect_to": [
        "accounts",
        "categories",
        "locations",
        "businesses",
        "services",
        "schedules",
        "appointments",
        "payments",
        "reviews",
        "portfolios",
        "ads",
        "explore",
        "reminders",
        "favorites",
        "search",
        "support",
        "notifications",
        "landing",
        "auth",
    ],
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "sidebar_fixed": True,
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "cosmo",
    "dark_mode_theme": None,
    "actions_sticky_top": True,
}

# ═══════════════════════════════════════════════
#   Celery Beat Schedule
# ═══════════════════════════════════════════════
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'daily-booking-reminders': {
        'task': 'apps.notifications.tasks.send_booking_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
    'same-day-booking-reminders': {
        'task': 'apps.notifications.tasks.send_same_day_reminders',
        'schedule': crontab(minute=0),
    },
    'check-renewal-reminders': {
        'task': 'apps.reminders.tasks.check_renewal_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
    'auto-settle-appointments': {
        'task': 'apps.payments.tasks.auto_settle_completed_appointments',
        'schedule': crontab(minute=0),
    },
    'process-pending-settlements': {
        'task': 'apps.payments.tasks.process_pending_settlements',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'verify-unconfirmed-payments': {
        'task': 'apps.notifications.tasks.verify_unconfirmed_payments',
        'schedule': crontab(minute='*/5'),
    },
    'cleanup-old-notifications': {
        'task': 'apps.notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=3, minute=0),
    },
    'cleanup-old-otp-codes': {
        'task': 'apps.notifications.tasks.cleanup_old_otp_codes',
        'schedule': crontab(hour=4, minute=0),
    },
}