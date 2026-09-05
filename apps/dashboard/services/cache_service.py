# apps/dashboard/services/cache_service.py

"""
سرویس کش داشبورد ادمین
✅ فاز ۵: بهبود استراتژی کش + افزودن کش‌های جدید

استراتژی کش (نسخه نهایی):
- آمار داشبورد: ۶۰ ثانیه
- نقش‌های ادمین: ۵ دقیقه
- قالب‌های پیامک: ۵ دقیقه
- تنظیمات سیستم: ۵ دقیقه
- تنظیمات لندینگ: ۵ دقیقه
- آمار ادمین‌ها: ۵ دقیقه
- لیست دسته‌بندی‌ها: ۱۰ دقیقه (جدید — فاز ۵)
- لیست استان‌ها/شهرها: ۱۰ دقیقه (جدید — فاز ۵)
"""

import logging

from django.core.cache import cache


logger = logging.getLogger(__name__)


# ─── TTL‌ها (ثانیه) ───
DASHBOARD_STATS_TTL = 60       # فاز ۵: از ۳۰ به ۶۰ افزایش یافت
ADMIN_ROLES_TTL = 300          # نقش‌ها: ۵ دقیقه
SMS_TEMPLATES_TTL = 300        # قالب‌های پیامک: ۵ دقیقه
SYSTEM_SETTINGS_TTL = 300      # تنظیمات سیستم: ۵ دقیقه
LANDING_SETTINGS_TTL = 300     # تنظیمات لندینگ: ۵ دقیقه
ADMIN_STATS_TTL = 300          # آمار ادمین‌ها: ۵ دقیقه
CATEGORIES_TTL = 600           # ✅ فاز ۵: دسته‌بندی‌ها: ۱۰ دقیقه
LOCATIONS_TTL = 600            # ✅ فاز ۵: استان‌ها/شهرها: ۱۰ دقیقه
BUSINESS_CATEGORIES_TTL = 600  # ✅ فاز ۵: انواع کسب‌وکار: ۱۰ دقیقه


# ─── کلیدهای کش ───
class CacheKeys:
    """کلیدهای کش داشبورد"""

    DASHBOARD_STATS = "dashboard:home_stats"
    ADMIN_ROLES_LIST = "dashboard:admin_roles_list"
    SMS_TEMPLATES_LIST = "dashboard:sms_templates_list"
    SYSTEM_SETTINGS = "dashboard:system_settings"
    LANDING_SETTINGS = "dashboard:landing_settings"
    ADMIN_STATS = "dashboard:admin_stats"

    # ✅ فاز ۵: کلیدهای جدید
    SERVICE_CATEGORIES = "dashboard:service_categories"
    BUSINESS_CATEGORIES = "dashboard:business_categories"
    PROVINCES = "dashboard:provinces"
    CITIES = "dashboard:cities"
    SUB_SERVICES = "dashboard:sub_services"


class DashboardCacheService:
    """سرویس کش داشبورد"""

    # ═══════════════════════════════════════════
    #   آمار داشبورد
    # ═══════════════════════════════════════════

    @classmethod
    def get_dashboard_stats(cls):
        """دریافت آمار داشبورد از کش"""
        return cache.get(CacheKeys.DASHBOARD_STATS)

    @classmethod
    def set_dashboard_stats(cls, data):
        """ذخیره آمار داشبورد در کش"""
        cache.set(
            CacheKeys.DASHBOARD_STATS,
            data,
            DASHBOARD_STATS_TTL,
        )

    @classmethod
    def invalidate_dashboard_stats(cls):
        """بی‌اعتبار کردن کش آمار داشبورد"""
        cache.delete(CacheKeys.DASHBOARD_STATS)

    # ═══════════════════════════════════════════
    #   نقش‌های ادمین
    # ═══════════════════════════════════════════

    @classmethod
    def get_admin_roles(cls):
        """دریافت نقش‌ها از کش"""
        return cache.get(CacheKeys.ADMIN_ROLES_LIST)

    @classmethod
    def set_admin_roles(cls, data):
        """ذخیره نقش‌ها در کش"""
        cache.set(
            CacheKeys.ADMIN_ROLES_LIST,
            data,
            ADMIN_ROLES_TTL,
        )

    @classmethod
    def invalidate_admin_roles(cls):
        """بی‌اعتبار کردن کش نقش‌ها"""
        cache.delete(CacheKeys.ADMIN_ROLES_LIST)

    # ═══════════════════════════════════════════
    #   قالب‌های پیامک
    # ═══════════════════════════════════════════

    @classmethod
    def get_sms_templates(cls):
        """دریافت قالب‌های پیامک از کش"""
        return cache.get(CacheKeys.SMS_TEMPLATES_LIST)

    @classmethod
    def set_sms_templates(cls, data):
        """ذخیره قالب‌ها در کش"""
        cache.set(
            CacheKeys.SMS_TEMPLATES_LIST,
            data,
            SMS_TEMPLATES_TTL,
        )

    @classmethod
    def invalidate_sms_templates(cls):
        """بی‌اعتبار کردن کش قالب‌ها"""
        cache.delete(CacheKeys.SMS_TEMPLATES_LIST)

    # ═══════════════════════════════════════════
    #   تنظیمات سیستم
    # ═══════════════════════════════════════════

    @classmethod
    def get_system_settings(cls):
        """دریافت تنظیمات سیستم از کش"""
        return cache.get(CacheKeys.SYSTEM_SETTINGS)

    @classmethod
    def set_system_settings(cls, data):
        """ذخیره تنظیمات سیستم در کش"""
        cache.set(
            CacheKeys.SYSTEM_SETTINGS,
            data,
            SYSTEM_SETTINGS_TTL,
        )

    @classmethod
    def invalidate_system_settings(cls):
        """بی‌اعتبار کردن کش تنظیمات سیستم"""
        cache.delete(CacheKeys.SYSTEM_SETTINGS)

    # ═══════════════════════════════════════════
    #   تنظیمات لندینگ
    # ═══════════════════════════════════════════

    @classmethod
    def get_landing_settings(cls):
        """دریافت تنظیمات لندینگ از کش"""
        return cache.get(CacheKeys.LANDING_SETTINGS)

    @classmethod
    def set_landing_settings(cls, data):
        """ذخیره تنظیمات لندینگ در کش"""
        cache.set(
            CacheKeys.LANDING_SETTINGS,
            data,
            LANDING_SETTINGS_TTL,
        )

    @classmethod
    def invalidate_landing_settings(cls):
        """بی‌اعتبار کردن کش تنظیمات لندینگ"""
        cache.delete(CacheKeys.LANDING_SETTINGS)

    # ═══════════════════════════════════════════
    #   آمار ادمین‌ها
    # ═══════════════════════════════════════════

    @classmethod
    def get_admin_stats(cls):
        """دریافت آمار ادمین‌ها از کش"""
        return cache.get(CacheKeys.ADMIN_STATS)

    @classmethod
    def set_admin_stats(cls, data):
        """ذخیره آمار ادمین‌ها در کش"""
        cache.set(
            CacheKeys.ADMIN_STATS,
            data,
            ADMIN_STATS_TTL,
        )

    @classmethod
    def invalidate_admin_stats(cls):
        """بی‌اعتبار کردن کش آمار ادمین‌ها"""
        cache.delete(CacheKeys.ADMIN_STATS)

    # ═══════════════════════════════════════════
    #   ✅ فاز ۵: کش دسته‌بندی‌ها (جدید)
    # ═══════════════════════════════════════════

    @classmethod
    def get_service_categories(cls):
        """دریافت دسته‌بندی‌های خدمات از کش"""
        return cache.get(CacheKeys.SERVICE_CATEGORIES)

    @classmethod
    def set_service_categories(cls, data):
        """ذخیره دسته‌بندی‌های خدمات در کش"""
        cache.set(
            CacheKeys.SERVICE_CATEGORIES,
            data,
            CATEGORIES_TTL,
        )

    @classmethod
    def invalidate_service_categories(cls):
        """بی‌اعتبار کردن کش دسته‌بندی‌ها"""
        cache.delete(CacheKeys.SERVICE_CATEGORIES)

    @classmethod
    def get_business_categories(cls):
        """دریافت انواع کسب‌وکار از کش"""
        return cache.get(CacheKeys.BUSINESS_CATEGORIES)

    @classmethod
    def set_business_categories(cls, data):
        """ذخیره انواع کسب‌وکار در کش"""
        cache.set(
            CacheKeys.BUSINESS_CATEGORIES,
            data,
            BUSINESS_CATEGORIES_TTL,
        )

    @classmethod
    def invalidate_business_categories(cls):
        """بی‌اعتبار کردن کش انواع کسب‌وکار"""
        cache.delete(CacheKeys.BUSINESS_CATEGORIES)

    @classmethod
    def get_provinces(cls):
        """دریافت استان‌ها از کش"""
        return cache.get(CacheKeys.PROVINCES)

    @classmethod
    def set_provinces(cls, data):
        """ذخیره استان‌ها در کش"""
        cache.set(
            CacheKeys.PROVINCES,
            data,
            LOCATIONS_TTL,
        )

    @classmethod
    def invalidate_provinces(cls):
        """بی‌اعتبار کردن کش استان‌ها"""
        cache.delete(CacheKeys.PROVINCES)

    @classmethod
    def get_cities(cls, province_id=None):
        """دریافت شهرها از کش"""
        key = CacheKeys.CITIES

        if province_id:
            key = f"{CacheKeys.CITIES}_{province_id}"

        return cache.get(key)

    @classmethod
    def set_cities(cls, data, province_id=None):
        """ذخیره شهرها در کش"""
        key = CacheKeys.CITIES

        if province_id:
            key = f"{CacheKeys.CITIES}_{province_id}"

        cache.set(
            key,
            data,
            LOCATIONS_TTL,
        )

    @classmethod
    def invalidate_cities(cls, province_id=None):
        """بی‌اعتبار کردن کش شهرها"""
        if province_id:
            cache.delete(f"{CacheKeys.CITIES}_{province_id}")
        else:
            # بی‌اعتبار کردن همه شهرها
            cache.delete_pattern(f"{CacheKeys.CITIES}_*")
            cache.delete(CacheKeys.CITIES)

    @classmethod
    def get_sub_services(cls, category_id=None):
        """دریافت زیرخدمات از کش"""
        key = CacheKeys.SUB_SERVICES

        if category_id:
            key = f"{CacheKeys.SUB_SERVICES}_{category_id}"

        return cache.get(key)

    @classmethod
    def set_sub_services(cls, data, category_id=None):
        """ذخیره زیرخدمات در کش"""
        key = CacheKeys.SUB_SERVICES

        if category_id:
            key = f"{CacheKeys.SUB_SERVICES}_{category_id}"

        cache.set(
            key,
            data,
            CATEGORIES_TTL,
        )

    @classmethod
    def invalidate_sub_services(cls, category_id=None):
        """بی‌اعتبار کردن کش زیرخدمات"""
        if category_id:
            cache.delete(f"{CacheKeys.SUB_SERVICES}_{category_id}")
        else:
            cache.delete_pattern(f"{CacheKeys.SUB_SERVICES}_*")
            cache.delete(CacheKeys.SUB_SERVICES)

    # ═══════════════════════════════════════════
    #   بی‌اعتبار کردن کلی
    # ═══════════════════════════════════════════

    @classmethod
    def invalidate_all(cls):
        """بی‌اعتبار کردن تمام کش‌های داشبورد"""

        keys = [
            CacheKeys.DASHBOARD_STATS,
            CacheKeys.ADMIN_ROLES_LIST,
            CacheKeys.SMS_TEMPLATES_LIST,
            CacheKeys.SYSTEM_SETTINGS,
            CacheKeys.LANDING_SETTINGS,
            CacheKeys.ADMIN_STATS,

            # ✅ فاز ۵: کلیدهای جدید
            CacheKeys.SERVICE_CATEGORIES,
            CacheKeys.BUSINESS_CATEGORIES,
            CacheKeys.PROVINCES,
            CacheKeys.CITIES,
            CacheKeys.SUB_SERVICES,
        ]

        for key in keys:
            cache.delete(key)

        logger.info("All dashboard caches invalidated")

    @classmethod
    def invalidate_all_lookup_data(cls):
        """
        ✅ فاز ۵: بی‌اعتبار کردن تمام داده‌های کم‌تغییر
        (دسته‌بندی‌ها، استان‌ها، شهرها، زیرخدمات)

        این متد وقتی صدا زده شود که داده‌های پایه تغییر کرده باشند.
        """

        cls.invalidate_service_categories()
        cls.invalidate_business_categories()
        cls.invalidate_provinces()
        cls.invalidate_cities()
        cls.invalidate_sub_services()

        logger.info("All lookup data caches invalidated")