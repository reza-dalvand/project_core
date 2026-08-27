"""
اعتبارسنج‌های سفارشی
"""
import re
from django.core.exceptions import ValidationError
from .utils import to_english_digits


def validate_iranian_phone(value):
    """اعتبارسنجی شماره موبایل ایران"""
    cleaned = to_english_digits(str(value)).strip()
    if cleaned.startswith('+98'):
        cleaned = '0' + cleaned[3:]
    elif cleaned.startswith('0098'):
        cleaned = '0' + cleaned[4:]
    if not re.match(r'^09[0-9]{9}$', cleaned):
        raise ValidationError(
            'شماره موبایل معتبر نیست. فرمت صحیح: ۰۹۱۲۳۴۵۶۷۸۹'
        )
    return cleaned


def validate_national_id(value):
    """اعتبارسنجی کد ملی ایران"""
    cleaned = to_english_digits(str(value)).strip()
    if len(cleaned) != 10:
        raise ValidationError('کد ملی باید دقیقاً ۱۰ رقم باشد')
    if len(set(cleaned)) == 1:
        raise ValidationError('کد ملی معتبر نیست')
    check = int(cleaned[9])
    total = sum(int(cleaned[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    if remainder < 2:
        if check != remainder:
            raise ValidationError('کد ملی معتبر نیست')
    else:
        if check != (11 - remainder):
            raise ValidationError('کد ملی معتبر نیست')
    return cleaned


def validate_sheba(value):
    """اعتبارسنجی شماره شبا"""
    cleaned = to_english_digits(str(value)).strip().upper()
    if not cleaned.startswith('IR'):
        raise ValidationError('شماره شبا باید با IR شروع شود')
    digits = cleaned.replace('IR', '').replace(' ', '')
    if len(digits) != 24:
        raise ValidationError('شماره شبا باید ۲۴ رقم بعد از IR باشد')
    if not digits.isdigit():
        raise ValidationError('شماره شبا فقط باید شامل ارقام باشد')
    return f'IR{digits}'


def validate_card_number(value):
    """اعتبارسنجی شماره کارت بانکی"""
    cleaned = to_english_digits(str(value)).strip()
    cleaned = re.sub(r'[\s-]', '', cleaned)
    if len(cleaned) != 16:
        raise ValidationError('شماره کارت باید ۱۶ رقم باشد')
    if not cleaned.isdigit():
        raise ValidationError('شماره کارت فقط باید شامل ارقام باشد')
    return cleaned