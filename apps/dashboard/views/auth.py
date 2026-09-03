"""
احراز هویت داشبورد ادمین با شماره تلفن + کد تایید
"""
import logging
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.accounts.models import OtpCode
from apps.accounts.services.otp_service import OTPService
from apps.core.exceptions import OTPException
from apps.core.utils import mask_phone, to_english_digits, normalize_phone
from apps.core.validators import validate_iranian_phone

logger = logging.getLogger(__name__)
User = get_user_model()

# نقش‌های داشبورد
ADMIN_ROLES = {
    'super_admin': 'سوپر ادمین',
    'app_admin': 'ادمین اپلیکیشن',
    'content_admin': 'ادمین محتوا',
    'financial_admin': 'ادمین مالی',
    'support_admin': 'پشتیبانی',
}

# شماره‌های مجاز برای هر نقش
# در فاز بعدی اینها را از دیتابیس یا تنظیمات می‌خوانیم
ALLOWED_ADMINS = {
    # شماره تلفن: نقش
    # '09120000000': 'super_admin',
}


def get_admin_role(phone):
    """
    دریافت نقش ادمین بر اساس شماره تلفن
    در فاز بعدی از دیتابیس خوانده می‌شود
    """
    # فعلاً: هر کاربر is_staff می‌تواند وارد شود
    try:
        user = User.objects.filter(
            phone=phone,
            is_staff=True,
            is_active=True,
        ).first()
        if user:
            return 'super_admin'  # فعلاً همه سوپر ادمین
    except Exception:
        pass
    return None


def login_view(request):
    """
    صفحه ورود — مرحله اول: شماره تلفن
    """
    # اگر قبلاً لاگین شده
    if request.session.get('dashboard_admin_logged_in'):
        return redirect(reverse('dashboard:home'))

    error = ''
    phone = ''

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        try:
            phone = validate_iranian_phone(phone)
        except ValidationError as e:
            error = e.messages[0] if hasattr(e, 'messages') else 'شماره موبایل معتبر نیست'
            return render(request, 'dashboard/auth/login.html', {
                'error': error,
                'phone': phone,
            })

        # بررسی مجاز بودن شماره
        role = get_admin_role(phone)
        if not role:
            error = 'این شماره دسترسی به پنل مدیریت ندارد.'
            return render(request, 'dashboard/auth/login.html', {
                'error': error,
                'phone': phone,
            })

        # ارسال کد تایید
        try:
            OTPService.send_otp(
                phone=phone,
                purpose=OtpCode.Purpose.ADMIN_LOGIN,
            )
            request.session['dashboard_otp_phone'] = phone
            request.session['dashboard_otp_role'] = role
            request.session['dashboard_otp_attempts'] = 0

            messages.success(
                request,
                f'کد تایید به شماره {mask_phone(phone)} ارسال شد.'
            )
            return redirect(reverse('dashboard:verify_otp'))

        except OTPException as e:
            error = e.message

    return render(request, 'dashboard/auth/login.html', {
        'error': error,
        'phone': phone,
    })


def verify_otp_view(request):
    """
    صفحه تایید کد — مرحله دوم
    """
    phone = request.session.get('dashboard_otp_phone')
    if not phone:
        return redirect(reverse('dashboard:login'))

    # اگر قبلاً لاگین شده
    if request.session.get('dashboard_admin_logged_in'):
        return redirect(reverse('dashboard:home'))

    error = ''
    masked_phone = mask_phone(phone)

    if request.method == 'POST':
        code = to_english_digits(request.POST.get('code', '')).strip()

        if not code.isdigit() or len(code) != 5:
            error = 'کد تایید باید ۵ رقم باشد.'
            return render(request, 'dashboard/auth/verify_otp.html', {
                'error': error,
                'masked_phone': masked_phone,
            })

        # بررسی تعداد تلاش‌ها
        attempts = request.session.get('dashboard_otp_attempts', 0)
        if attempts >= 5:
            request.session.pop('dashboard_otp_phone', None)
            request.session.pop('dashboard_otp_role', None)
            request.session.pop('dashboard_otp_attempts', None)
            messages.error(request, 'تعداد تلاش‌ها بیش از حد مجاز است.')
            return redirect(reverse('dashboard:login'))

        # تایید کد
        try:
            OTPService.verify_otp(
                phone=phone,
                code=code,
                purpose=OtpCode.Purpose.ADMIN_LOGIN,
            )
        except OTPException as e:
            request.session['dashboard_otp_attempts'] = attempts + 1
            error = e.message
            return render(request, 'dashboard/auth/verify_otp.html', {
                'error': error,
                'masked_phone': masked_phone,
            })

        # ✅ ورود موفق
        role = request.session.get('dashboard_otp_role', 'super_admin')

        request.session['dashboard_admin_logged_in'] = True
        request.session['dashboard_admin_phone'] = phone
        request.session['dashboard_role'] = role
        request.session['dashboard_login_time'] = timezone.now().isoformat()

        # پاک کردن داده‌های موقت
        request.session.pop('dashboard_otp_phone', None)
        request.session.pop('dashboard_otp_role', None)
        request.session.pop('dashboard_otp_attempts', None)

        logger.info(f"Admin logged in: {phone} ({role})")
        messages.success(request, 'ورود موفقیت‌آمیز بود.')
        return redirect(reverse('dashboard:home'))

    return render(request, 'dashboard/auth/verify_otp.html', {
        'masked_phone': masked_phone,
        'error': error,
    })


def resend_otp_view(request):
    """ارسال مجدد کد تایید"""
    phone = request.session.get('dashboard_otp_phone')
    if not phone:
        return redirect(reverse('dashboard:login'))

    try:
        OTPService.send_otp(
            phone=phone,
            purpose=OtpCode.Purpose.ADMIN_LOGIN,
        )
        messages.success(request, 'کد تایید مجدداً ارسال شد.')
    except OTPException as e:
        messages.error(request, e.message)

    return redirect(reverse('dashboard:verify_otp'))


def logout_view(request):
    """خروج از داشبورد"""
    request.session.pop('dashboard_admin_logged_in', None)
    request.session.pop('dashboard_admin_phone', None)
    request.session.pop('dashboard_role', None)
    request.session.pop('dashboard_login_time', None)
    messages.info(request, 'با موفقیت خارج شدید.')
    return redirect(reverse('dashboard:login'))