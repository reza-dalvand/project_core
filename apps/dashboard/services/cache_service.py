# apps/dashboard/services/cache_service.py
"""
سرویس کش داشبورد ادمین
✅ فاز ۵: کش‌سازی داده‌های کم‌تغییر برای کاهش فشار دیتابیس

استراتژی کش:
- آمار داشبورد: ۳۰ ثانیه (تغییرات مکرر)
- نقش‌های ادمین: ۵ دقیقه (تغییرات نادر)
- قالب‌های پیامک: ۵ دقیقه (تغییرات نادر)
- تنظیمات سیستم: ۵ دقیقه (تغییرات نادر)
- تنظیمات لندینگ: ۵ دقیقه (تغییرات نادر)
"""
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ─── TTL‌ها (ثانیه) ───
DASHBOARD_STATS_TTL = 30       # آمار داشبورد: ۳۰ ثانیه
ADMIN_ROLES_TTL = 300          # نقش‌ها: ۵ دقیقه
SMS_TEMPLATES_TTL = 300        # قالب‌های پیامک: ۵ دقیقه
SYSTEM_SETTINGS_TTL = 300      # تنظیمات سیستم: ۵ دقیقه
LANDING_SETTINGS_TTL = 300     # تنظیمات لندینگ: ۵ دقیقه
ADMIN_STATS_TTL = 300          # آمار ادمین‌ها: ۵ دقیقه


# ─── کلیدهای کش ───
class CacheKeys:
    """کلیدهای کش داشبورد"""
    DASHBOARD_STATS = 'dashboard:home_stats'
    ADMIN_ROLES_LIST = 'dashboard:admin_roles_list'
    SMS_TEMPLATES_LIST = 'dashboard:sms_templates_list'
    SYSTEM_SETTINGS = 'dashboard:system_settings'
    LANDING_SETTINGS = 'dashboard:landing_settings'
    ADMIN_STATS = 'dashboard:admin_stats'


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
        cache.set(CacheKeys.DASHBOARD_STATS, data, DASHBOARD_STATS_TTL)

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
        cache.set(CacheKeys.ADMIN_ROLES_LIST, data, ADMIN_ROLES_TTL)

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
        cache.set(CacheKeys.SMS_TEMPLATES_LIST, data, SMS_TEMPLATES_TTL)

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
        cache.set(CacheKeys.SYSTEM_SETTINGS, data, SYSTEM_SETTINGS_TTL)

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
        cache.set(CacheKeys.LANDING_SETTINGS, data, LANDING_SETTINGS_TTL)

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
        cache.set(CacheKeys.ADMIN_STATS, data, ADMIN_STATS_TTL)

    @classmethod
    def invalidate_admin_stats(cls):
        """بی‌اعتبار کردن کش آمار ادمین‌ها"""
        cache.delete(CacheKeys.ADMIN_STATS)

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
        ]
        for key in keys:
            cache.delete(key)
        logger.info("All dashboard caches invalidated")