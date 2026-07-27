"""
توابع کمکی مشترک برای کل پروژه
"""
import random
import string
import jdatetime
from django.utils import timezone


def now_jalali():
    """تاریخ و زمان فعلی به شمسی"""
    return jdatetime.datetime.fromgregorian(datetime=timezone.now())


def today_jalali():
    """تاریخ امروز به شمسی"""
    return jdatetime.date.today()


def format_price(amount):
    """فرمت قیمت به فارسی با جداکننده هزارگان"""
    if amount is None:
        return '۰ تومان'
    try:
        amount = int(amount)
        formatted = f'{amount:,}'.translate(
            str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
        )
        return f'{formatted} تومان'
    except (ValueError, TypeError):
        return str(amount)


def to_persian_digits(text):
    """تبدیل اعداد انگلیسی به فارسی"""
    if text is None:
        return ''
    return str(text).translate(
        str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    )


def to_english_digits(text):
    """تبدیل اعداد فارسی/عربی به انگلیسی"""
    if text is None:
        return ''
    return (
        str(text)
        .translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))
        .translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
    )


def generate_otp(length=5):
    """تولید کد تایید (OTP) تصادفی"""
    digits = string.digits
    return ''.join(random.choices(digits, k=length))


def generate_verification_code(length=4):
    """تولید کد تایید نوبت ۴ رقمی"""
    return ''.join(random.choices(string.digits, k=length))


def generate_tracking_code():
    """تولید کد پیگیری تراکنش"""
    random_part = ''.join(random.choices(string.digits, k=10))
    return f'TRK-{random_part}'


def generate_ref_number():
    """تولید شماره ارجاع"""
    now = now_jalali()
    random_part = ''.join(random.choices(string.digits, k=6))
    return f'REF-{now.year}-{random_part}'


def normalize_phone(phone):
    """نرمال‌سازی شماره موبایل"""
    if not phone:
        return None
    cleaned = to_english_digits(str(phone)).strip()
    cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '+')

    if cleaned.startswith('+98'):
        cleaned = '0' + cleaned[3:]
    elif cleaned.startswith('0098'):
        cleaned = '0' + cleaned[4:]

    return cleaned


def mask_phone(phone):
    """مخفی‌سازی شماره موبایل"""
    if not phone or len(phone) < 11:
        return phone
    return f'{phone[:4]}***{phone[-4:]}'


def get_client_ip(request):
    """استخراج IP کاربر"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_device_info(request):
    """استخراج اطلاعات دستگاه از User-Agent"""
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    # تشخیص نوع دستگاه
    device_type = 'unknown'
    if 'Android' in user_agent:
        device_type = 'android'
    elif 'iPhone' in user_agent or 'iPad' in user_agent or 'iOS' in user_agent:
        device_type = 'ios'
    elif 'Mozilla' in user_agent or 'Chrome' in user_agent or 'Safari' in user_agent:
        device_type = 'web'

    # استخراج نسخه اپ (از header سفارشی)
    app_version = request.META.get('HTTP_X_APP_VERSION', '')
    device_name = request.META.get('HTTP_X_DEVICE_NAME', '')
    os_version = request.META.get('HTTP_X_OS_VERSION', '')

    return {
        'device_type': device_type,
        'device_name': device_name,
        'os_version': os_version,
        'app_version': app_version,
    }