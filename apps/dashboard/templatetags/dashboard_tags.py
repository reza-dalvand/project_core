# apps/dashboard/templatetags/dashboard_tags.py
"""
تمپلیت تگ‌های سفارشی داشبورد ادمین
✅ فاز ۱: فیلتر url_in برای تشخیص دقیق آیتم فعال منو
"""
from django import template

register = template.Library()


@register.filter(name='url_in')
def url_in_filter(url_name, names):
    """
    بررسی اینکه url_name دقیقاً در لیست نام‌ها باشد.

    استفاده در تمپلیت:
        {% if request.resolver_match.url_name|url_in:'businesses_list,business_detail' %}
            active
        {% endif %}

    ✅ برخلاف عملگر in پایتون روی رشته، اینجا تطابق دقیق است
    نه جستجوی زیررشته. یعنی 'list' با 'businesses_list'
    اشتباهاً مطابقت نمی‌کند.

    Args:
        url_name: نام URL فعلی (مثلاً 'businesses_list')
        names: رشته کاما-جدا از نام‌های مجاز (مثلاً 'businesses_list,business_detail')

    Returns:
        bool: آیا url_name دقیقاً در لیست وجود دارد؟
    """
    if not url_name or not names:
        return False
    allowed = [n.strip() for n in names.split(',')]
    return url_name in allowed