"""
Jinja2 Environment Configuration
"""
from jinja2 import Environment
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.utils import translation


def environment(**options):
    """
    Create and configure the Jinja2 environment.
    """
    env = Environment(**options)

    # ─── Globals (متغیرهای در دسترس در همه تمپلیت‌ها) ───
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
        'now': _now,
        'get_language': translation.get_language,
    })

    # ─── Filters (فیلترهای قابل استفاده با | ) ───
    env.filters.update({
        'to_persian_digit': _to_persian_digit,
        'format_price': _format_price,
        'truncate_words': _truncate_words,
    })

    return env


def _now():
    """Return current datetime."""
    from django.utils import timezone
    return timezone.now()


def _to_persian_digit(value):
    """Convert English digits to Persian."""
    if value is None:
        return ''
    return str(value).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))


def _format_price(value):
    """Format number as Persian price."""
    if value is None:
        return '۰'
    try:
        num = int(value)
        formatted = f'{num:,}'.translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        return f'{formatted} تومان'
    except (ValueError, TypeError):
        return str(value)


def _truncate_words(value, length=30):
    """Truncate text to specified word count."""
    if not value:
        return ''
    words = str(value).split()
    if len(words) <= length:
        return value
    return ' '.join(words[:length]) + '...'