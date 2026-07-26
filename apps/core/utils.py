"""
توابع کمکی مشترک برای کل پروژه
"""
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
    import random
    digits = '0123456789'
    return ''.join(random.choices(digits, k=length))


def generate_verification_code(length=4):
    """تولید کد تایید نوبت ۴ رقمی"""
    import random
    return ''.join(random.choices('0123456789', k=length))


def generate_tracking_code():
    """تولید کد پیگیری تراکنش"""
    import random
    import string
    prefix = 'TRK'
    random_part = ''.join(random.choices(string.digits, k=10))
    return f'{prefix}-{random_part}'


def generate_ref_number():
    """تولید شماره ارجاع"""
    import random
    now = now_jalali()
    random_part = ''.join(random.choices('0123456789', k=3))
    return f'REF-{now.year}-{random_part}'