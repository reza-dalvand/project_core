# apps/dashboard/templatetags/dashboard_tags.py
"""
تمپلیت تگ‌های سفارشی داشبورد ادمین
✅ فاز ۲: افزودن فیلترهای ماسک‌سازی اطلاعات حساس
✅ فاز ۱: فیلتر url_in برای تشخیص دقیق آیتم فعال منو
"""
from django import template

register = template.Library()


@register.filter(name='url_in')
def url_in_filter(url_name, names):
    """
    بررسی اینکه url_name دقیقاً در لیست نام‌ها باشد.
    ✅ برخلاف عملگر in پایتون روی رشته، اینجا تطابق دقیق است
    """
    if not url_name or not names:
        return False
    allowed = [n.strip() for n in names.split(',')]
    return url_name in allowed


# ═══════════════════════════════════════════════
#   ✅ فاز ۲: فیلترهای ماسک‌سازی اطلاعات حساس
# ═══════════════════════════════════════════════
@register.filter(name='mask_sheba')
def mask_sheba(value):
    """
    ماسک‌سازی شماره شبا
    ورودی:  IR123456789012345678901234
    خروجی:  IR**************************34
    """
    if not value:
        return '-'
    value = str(value)
    if len(value) < 6:
        return value[:2] + '*' * (len(value) - 2)
    return value[:2] + '*' * (len(value) - 4) + value[-2:]


@register.filter(name='mask_card')
def mask_card(value):
    """
    ماسک‌سازی شماره کارت
    ورودی:  6037123456789012
    خروجی:  6037********9012
    """
    if not value:
        return '-'
    value = str(value)
    if len(value) < 8:
        return value[:4] + '*' * (len(value) - 4)
    return value[:4] + '*' * (len(value) - 8) + value[-4:]


@register.filter(name='mask_account')
def mask_account(value):
    """
    ماسک‌سازی شماره حساب
    ورودی:  0123456789
    خروجی:  012****789
    """
    if not value:
        return '-'
    value = str(value)
    if len(value) < 6:
        return value[:3] + '*' * (len(value) - 3)
    return value[:3] + '*' * (len(value) - 6) + value[-3:]


@register.filter(name='mask_national_id')
def mask_national_id(value):
    """
    ماسک‌سازی کد ملی
    ورودی:  0012345679
    خروجی:  001****679
    """
    if not value:
        return '-'
    value = str(value)
    if len(value) < 6:
        return value[:3] + '*' * (len(value) - 3)
    return value[:3] + '*' * (len(value) - 6) + value[-3:]


@register.filter(name='mask_phone_number')
def mask_phone_number(value):
    """
    ماسک‌سازی شماره موبایل
    ورودی:  09123456789
    خروجی:  0912***6789
    """
    if not value:
        return '-'
    value = str(value)
    if len(value) < 7:
        return value[:4] + '*' * (len(value) - 4)
    return value[:4] + '*' * (len(value) - 7) + value[-4:]