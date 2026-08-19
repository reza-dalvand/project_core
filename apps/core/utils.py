"""
توابع کمکی مشترک برای کل پروژه
"""
import random
import string
import jdatetime
from django.utils import timezone


# ═══════════════════════════════════════════════
#   تاریخ جلالی
# ═══════════════════════════════════════════════

def jalali_to_key(jy: int, jm: int, jd: int) -> str:
    """تبدیل تاریخ جلالی به کلید یکتا"""
    return f"{jy}/{jm:02d}/{jd:02d}"


def today_jalali_key() -> str:
    """کلید تاریخ امروز جلالی"""
    today = jdatetime.date.today()
    return jalali_to_key(today.jyear, today.jmonth, today.jday)


def now_jalali():
    """تاریخ و زمان فعلی به شمسی"""
    return jdatetime.datetime.fromgregorian(datetime=timezone.now())


def today_jalali():
    """تاریخ امروز به شمسی"""
    return jdatetime.date.today()


def jalali_days_remaining(due_date_key: str) -> int:
    """محاسبه تعداد روزهای باقی‌مانده تا تاریخ جلالی"""
    try:
        parts = due_date_key.split('/')
        jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
        due_date = jdatetime.date(jy, jm, jd)
        today = jdatetime.date.today()
        return (due_date - today).days
    except (ValueError, IndexError):
        return 0


# apps/core/utils.py
# ═══════════════════════════════════════════════
#   محاسبه کمیسیون — نسخه نهایی (هماهنگ با فرانت)
# ═══════════════════════════════════════════════

# سقف کمیسیون بیو کلاب (تومان)
MAX_APP_FEE = 50000

def calculate_app_fee(amount: int) -> int:
    """
    محاسبه کمیسیون بیو کلاب بر اساس قیمت نهایی خدمت
    
    قوانین (هماهنگ با فرانت‌اند price-utils.js):
    - زیر ۲۵۰,۰۰۰ تومان: ۷,۰۰۰ تومان ثابت
    - از ۲۵۰,۰۰۰ تا ۵۰۰,۰۰۰ تومان: ۳٪
    - از ۵۰۰,۰۰۰ تومان به بالا: ۴٪
    - سقف: ۵۰,۰۰۰ تومان
    
    Args:
        amount: قیمت نهایی خدمت (تومان)
    Returns:
        مبلغ کمیسیون (تومان)
    """
    if not amount or amount <= 0:
        return 0
    
    if amount < 250000:
        # زیر ۲۵۰ هزار: ثابت ۷,۰۰۰
        fee = 7000
    elif amount <= 500000:
        # ۲۵۰ هزار تا ۵۰۰ هزار: ۳٪
        fee = int(amount * 0.03)
    else:
        # بالای ۵۰۰ هزار: ۴٪
        fee = int(amount * 0.04)
    
    # اعمال سقف
    return min(fee, MAX_APP_FEE)


# ═══════════════════════════════════════════════
#   اعداد و فرمت
# ═══════════════════════════════════════════════

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


# ═══════════════════════════════════════════════
#   تولید کد
# ═══════════════════════════════════════════════

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
    return f'REF-{now.jyear}-{random_part}'


def generate_booking_slug(length=8):
    """تولید اسلاگ یکتا برای لینک رزرو"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


# ═══════════════════════════════════════════════
#   موبایل
# ═══════════════════════════════════════════════

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


# ═══════════════════════════════════════════════
#   Request Info
# ═══════════════════════════════════════════════

def get_client_ip(request):
    """استخراج IP کاربر"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_device_info(request):
    """استخراج اطلاعات دستگاه از User-Agent"""
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    device_type = 'unknown'
    if 'Android' in user_agent:
        device_type = 'android'
    elif 'iPhone' in user_agent or 'iPad' in user_agent or 'iOS' in user_agent:
        device_type = 'ios'
    elif 'Mozilla' in user_agent or 'Chrome' in user_agent or 'Safari' in user_agent:
        device_type = 'web'

    app_version = request.META.get('HTTP_X_APP_VERSION', '')
    device_name = request.META.get('HTTP_X_DEVICE_NAME', '')
    os_version = request.META.get('HTTP_X_OS_VERSION', '')

    return {
        'device_type': device_type,
        'device_name': device_name,
        'os_version': os_version,
        'app_version': app_version,
    }