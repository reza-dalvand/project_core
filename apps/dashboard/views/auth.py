# apps/dashboard/views/auth.py
"""
احراز هویت داشبورد ادمین با شماره تلفن + کد تایید
✅ باگ‌فیکس: اصلاح get_admin_role + لاگ تشخیصی + هندل خطای کامل
"""
import logging
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.accounts.models import OtpCode
from apps.dashboard.models import AdminUser  # ✅ import اضافه شد
from apps.accounts.services.otp_service import OTPService
from apps.core.exceptions import OTPException
from apps.core.utils import mask_phone, to_english_digits
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


def get_admin_role(phone):
    """
    دریافت نقش واقعی ادمین از دیتابیس

    منطق اصلاح‌شده:
    1. کاربر is_staff=True و is_active=True باشد
    2. اگر AdminUser دارد و فعال است:
       - نقش دارد → نقش را برگردان
       - نقش ندارد → سوپر ادمین
    3. اگر AdminUser ندارد ولی is_staff است:
       → سوپر ادمین (قبلاً برمی‌گشت: None ← باگ!)
    4. اگر AdminUser دارد ولی is_active=False → None
    """
    try:
        user = User.objects.filter(
            phone=phone,
            is_staff=True,
            is_active=True,
        ).first()

        if not user:
            logger.info(
                f"Dashboard login rejected: "
                f"phone={phone} — not staff or not active"
            )
            return None

        # ─── بررسی پروفایل ادمین ───
        try:
            admin_profile = user.admin_profile  # OneToOneField

            if not admin_profile.is_active:
                logger.info(
                    f"Dashboard login rejected: "
                    f"phone={phone} — admin_profile inactive"
                )
                return None

            if admin_profile.role:
                logger.info(
                    f"Dashboard login role: "
                    f"phone={phone} — role={admin_profile.role.name}"
                )
                return admin_profile.role.name

            # نقش ندارد ولی فعال است
            return 'super_admin'

        except AdminUser.DoesNotExist:
            # ✅ FIX: کاربر is_staff=True است ولی AdminUser ندارد
            # قبلاً اینجا None برمی‌گشت و کاربر گیر می‌کرد
            logger.info(
                f"Dashboard login role: "
                f"phone={phone} — no AdminUser record, "
                f"treating as super_admin"
            )
            return 'super_admin'

    except Exception as e:
        logger.error(f"get_admin_role error: {e}", exc_info=True)
        return None


def login_view(request):
    """صفحه ورود — مرحله اول: شماره تلفن"""
    if request.session.get('dashboard_admin_logged_in'):
        return redirect(reverse('dashboard:home'))

    error = ''
    phone = ''

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()

        # ─── اعتبارسنجی شماره ───
        try:
            phone = validate_iranian_phone(phone)
        except ValidationError as e:
            error = (
                e.messages[0]
                if hasattr(e, 'messages') and e.messages
                else 'شماره موبایل معتبر نیست'
            )
            return render(request, 'dashboard/auth/login.html', {
                'error': error,
                'phone': phone,
            })

        # ─── بررسی مجاز بودن شماره ───
        role = get_admin_role(phone)
        if not role:
            error = 'این شماره دسترسی به پنل مدیریت ندارد.'
            logger.warning(
                f"Dashboard login blocked: phone={phone}"
            )
            return render(request, 'dashboard/auth/login.html', {
                'error': error,
                'phone': phone,
            })

        # ─── ارسال کد تایید ───
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
            logger.warning(
                f"Dashboard OTP send error: "
                f"phone={phone} — {e.message}"
            )

        except Exception as e:
            # ✅ FIX: قبلاً خطاهای غیرمنتظره هندل نمی‌شدند
            # و صفحه 500 خالی نمایش داده می‌شد
            logger.error(
                f"Dashboard login unexpected error: {e}",
                exc_info=True,
            )
            error = 'خطا در ارسال کد تایید. لطفاً دوباره تلاش کنید.'

    return render(request, 'dashboard/auth/login.html', {
        'error': error,
        'phone': phone,
    })


def verify_otp_view(request):
    """صفحه تایید کد — مرحله دوم"""
    phone = request.session.get('dashboard_otp_phone')
    if not phone:
        return redirect(reverse('dashboard:login'))

    user = User.objects.filter(
        phone=phone, is_staff=True, is_active=True
    ).first()
    if not user:
        messages.error(request, 'دسترسی شما لغو شده است.')
        return redirect(reverse('dashboard:login'))

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

        attempts = request.session.get('dashboard_otp_attempts', 0)
        if attempts >= 5:
            request.session.pop('dashboard_otp_phone', None)
            request.session.pop('dashboard_otp_role', None)
            request.session.pop('dashboard_otp_attempts', None)
            messages.error(request, 'تعداد تلاش‌ها بیش از حد مجاز است.')
            return redirect(reverse('dashboard:login'))

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

        # ✅ نقش از سشن — بدون پیش‌فرض خطرناک
        role = request.session.get('dashboard_otp_role')
        if not role:
            request.session.pop('dashboard_otp_phone', None)
            request.session.pop('dashboard_otp_role', None)
            request.session.pop('dashboard_otp_attempts', None)
            messages.error(
                request,
                'نشست شما منقضی شده است. لطفاً دوباره وارد شوید.'
            )
            return redirect(reverse('dashboard:login'))

        # ✅ ورود موفق
        request.session['dashboard_admin_logged_in'] = True
        request.session['dashboard_admin_phone'] = phone
        request.session['dashboard_role'] = role
        request.session['dashboard_login_time'] = timezone.now().isoformat()

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