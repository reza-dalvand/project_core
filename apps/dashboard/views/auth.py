# apps/dashboard/views/auth.py
"""
احراز هویت داشبورد ادمین با شماره تلفن + کد تایید
✅ فاز ۲: افزودن Rate Limiting + Session Fixation Fix
✅ فاز ۲: افزودن قفل حساب واقعی
✅ فاز ۲: افزودن لاگ امنیتی
✅ فاز ۱: فیکس هندل خطای کامل
"""
import logging
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.accounts.models import OtpCode
from apps.dashboard.models import AdminUser
from apps.accounts.services.otp_service import OTPService
from apps.core.exceptions import OTPException
from apps.core.utils import mask_phone, to_english_digits
from apps.core.validators import validate_iranian_phone

logger = logging.getLogger(__name__)

User = get_user_model()

# ═══════════════════════════════════════════════
#   تنظیمات امنیتی
# ═══════════════════════════════════════════════
_dashboard_settings = getattr(
    settings, 'DASHBOARD_SETTINGS', {}
)
MAX_OTP_ATTEMPTS = _dashboard_settings.get(
    'MAX_LOGIN_ATTEMPTS', 5
)
MAX_RESEND_ATTEMPTS = _dashboard_settings.get(
    'MAX_RESEND_ATTEMPTS', 3
)
LOGIN_LOCKOUT_MINUTES = _dashboard_settings.get(
    'LOGIN_LOCKOUT_MINUTES', 15
)
ENABLE_IP_RESTRICTION = _dashboard_settings.get(
    'ENABLE_IP_RESTRICTION', False
)
ALLOWED_IPS = _dashboard_settings.get('ALLOWED_IPS', [])


def _get_client_ip(request):
    """استخراج IP کاربر"""
    x_forwarded_for = request.META.get(
        'HTTP_X_FORWARDED_FOR'
    )
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _check_ip_allowed(request):
    """
    ✅ فاز ۲: بررسی محدودسازی بر اساس نقش در دکوراتور
    """
    if not ENABLE_IP_RESTRICTION:
        return True

    client_ip = _get_client_ip(request)

    if not ALLOWED_IPS:
        return True

    if client_ip not in ALLOWED_IPS:
        logger.warning(
            f"Dashboard access blocked by IP "
            f"restriction: ip={client_ip}"
        )
        return False

    return True


def _is_login_locked(phone):
    """
    ✅ فاز ۲: بررسی قفل بودن ورود
    """
    cache_key = f'dashboard_login_lock:{phone}'
    return cache.get(cache_key) is not None


def _increment_login_attempts(phone):
    """
    ✅ فاز ۲: افزایش شمارنده تلاش‌ها
    """
    cache_key = f'dashboard_login_attempts:{phone}'
    lock_key = f'dashboard_login_lock:{phone}'

    attempts = cache.get(cache_key, 0)
    attempts += 1
    cache.set(cache_key, attempts, timeout=3600)

    if attempts >= MAX_OTP_ATTEMPTS:
        cache.set(
            lock_key, True,
            timeout=LOGIN_LOCKOUT_MINUTES * 60
        )
        logger.warning(
            f"Dashboard login locked for "
            f"{phone} after {attempts} attempts"
        )


def get_admin_role(phone):
    """
    دریافت نقش واقعی ادمین از دیتابیس
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

        try:
            admin_profile = user.admin_profile
            if not admin_profile.is_active:
                logger.info(
                    f"Dashboard login rejected: "
                    f"phone={phone} — admin_profile inactive"
                )
                return None
            if admin_profile.role:
                logger.info(
                    f"Dashboard login role: "
                    f"phone={phone} — "
                    f"role={admin_profile.role.name}"
                )
                return admin_profile.role.name
            return 'super_admin'
        except AdminUser.DoesNotExist:
            logger.info(
                f"Dashboard login role: "
                f"phone={phone} — no AdminUser record, "
                f"treating as super_admin"
            )
            return 'super_admin'
    except Exception as e:
        logger.error(
            f"get_admin_role error: {e}",
            exc_info=True
        )
        return None


# ═══════════════════════════════════════════════
#   صفحه ورود
# ═══════════════════════════════════════════════
def login_view(request):
    """صفحه ورود — مرحله اول: شماره تلفن"""

    # ✅ فاز ۲: بررسی محدودسازی بر اساس نقش در دکوراتور
    if not _check_ip_allowed(request):
        error = (
            'دسترسی شما به پنل مدیریت از این آدرس '
            'محدود شده است.'
        )
        return render(
            request,
            'dashboard/auth/login.html',
            {'error': error, 'phone': ''},
        )

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
            return render(
                request,
                'dashboard/auth/login.html',
                {'error': error, 'phone': phone},
            )

        # ─── ✅ فاز ۲: بررسی قفل بودن شماره ───
        if _is_login_locked(phone):
            error = (
                f'تعداد تلاش‌های شما بیش از حد مجاز است. '
                f'لطفاً {LOGIN_LOCKOUT_MINUTES} دقیقه '
                f'صبر کنید.'
            )
            logger.warning(
                f"Dashboard login blocked: "
                f"phone={phone} — locked"
            )
            return render(
                request,
                'dashboard/auth/login.html',
                {'error': error, 'phone': phone},
            )

        # ─── بررسی مجاز بودن شماره ───
        role = get_admin_role(phone)
        if not role:
            # ✅ فاز ۲: ثبت تلاش ناموفق + قفل تدریجی
            _increment_login_attempts(phone)
            error = (
                'این شماره دسترسی به پنل مدیریت ندارد.'
            )
            logger.warning(
                f"Dashboard login blocked: phone={phone}"
            )
            return render(
                request,
                'dashboard/auth/login.html',
                {'error': error, 'phone': phone},
            )

        # ─── ارسال کد تایید ───
        try:
            OTPService.send_otp(
                phone=phone,
                purpose=OtpCode.Purpose.ADMIN_LOGIN,
            )
            request.session['dashboard_otp_phone'] = phone
            request.session['dashboard_otp_role'] = role
            request.session['dashboard_otp_attempts'] = 0
            request.session['dashboard_otp_resend_count'] = 0

            messages.success(
                request,
                f'کد تایید به شماره '
                f'{mask_phone(phone)} ارسال شد.'
            )
            return redirect(reverse('dashboard:verify_otp'))

        except OTPException as e:
            error = e.message
            logger.warning(
                f"Dashboard OTP send error: "
                f"phone={phone} — {e.message}"
            )

        except Exception as e:
            logger.error(
                f"Dashboard login unexpected error: {e}",
                exc_info=True,
            )
            error = (
                'خطا در ارسال کد تایید. '
                'لطفاً اتصال خود را بررسی و '
                'دوباره تلاش کنید.'
            )

    return render(
        request,
        'dashboard/auth/login.html',
        {'error': error, 'phone': phone},
    )


# ═══════════════════════════════════════════════
#   صفحه تایید کد
# ═══════════════════════════════════════════════
def verify_otp_view(request):
    """صفحه تایید کد — مرحله دوم"""
    phone = request.session.get('dashboard_otp_phone')
    if not phone:
        return redirect(reverse('dashboard:login'))

    if request.session.get('dashboard_admin_logged_in'):
        return redirect(reverse('dashboard:home'))

    error = ''
    masked_phone = mask_phone(phone)

    if request.method == 'POST':
        code = to_english_digits(
            request.POST.get('code', '')
        ).strip()

        # ─── اعتبارسنجی فرمت کد ───
        if not code.isdigit() or len(code) != 5:
            error = 'کد تایید باید ۵ رقم باشد.'
            return render(
                request,
                'dashboard/auth/verify_otp.html',
                {
                    'error': error,
                    'masked_phone': masked_phone,
                },
            )

        # ─── بررسی تعداد تلاش‌ها ───
        attempts = request.session.get(
            'dashboard_otp_attempts', 0
        )
        if attempts >= MAX_OTP_ATTEMPTS:
            # ✅ فاز ۲: قفل کردن شماره در کش
            _increment_login_attempts(phone)
            _clear_otp_session(request)
            messages.error(
                request,
                'تعداد تلاش‌ها بیش از حد مجاز است. '
                'لطفاً دوباره وارد شوید.'
            )
            return redirect(reverse('dashboard:login'))

        # ─── بررسی مجدد اعتبار کاربر ───
        try:
            user = User.objects.filter(
                phone=phone,
                is_staff=True,
                is_active=True,
            ).first()
            if not user:
                _clear_otp_session(request)
                messages.error(
                    request,
                    'دسترسی شما لغو شده است. '
                    'لطفاً با مدیر سیستم تماس بگیرید.'
                )
                return redirect(reverse('dashboard:login'))

            try:
                admin_profile = user.admin_profile
                if not admin_profile.is_active:
                    _clear_otp_session(request)
                    messages.error(
                        request,
                        'حساب ادمین شما غیرفعال شده است.'
                    )
                    return redirect(
                        reverse('dashboard:login')
                    )
            except AdminUser.DoesNotExist:
                pass

        except Exception as e:
            logger.error(
                f"verify_otp user check error: {e}",
                exc_info=True,
            )
            _clear_otp_session(request)
            messages.error(
                request,
                'خطا در بررسی وضعیت کاربر. '
                'دوباره تلاش کنید.'
            )
            return redirect(reverse('dashboard:login'))

        # ─── تایید کد ───
        try:
            OTPService.verify_otp(
                phone=phone,
                code=code,
                purpose=OtpCode.Purpose.ADMIN_LOGIN,
            )
        except OTPException as e:
            request.session['dashboard_otp_attempts'] = (
                attempts + 1
            )
            error = e.message
            return render(
                request,
                'dashboard/auth/verify_otp.html',
                {
                    'error': error,
                    'masked_phone': masked_phone,
                },
            )

        # ─── دریافت نقش از سشن ───
        role = request.session.get('dashboard_otp_role')
        if not role:
            _clear_otp_session(request)
            messages.error(
                request,
                'نشست شما منقضی شده است. '
                'لطفاً دوباره وارد شوید.'
            )
            return redirect(reverse('dashboard:login'))

        # ─── ✅ فاز ۲: جلوگیری از Session Fixation ───
        # تغییر Session ID پس از ورود موفق
        request.session.cycle_key()

        # ─── ورود موفق ───
        now = timezone.now()
        request.session['dashboard_admin_logged_in'] = True
        request.session['dashboard_admin_phone'] = phone
        request.session['dashboard_role'] = role
        request.session['dashboard_login_time'] = (
            now.isoformat()
        )
        # ✅ فاز ۲: ثبت زمان شروع مطلق سشن
        request.session['dashboard_session_start'] = (
            now.isoformat()
        )

        # پاک کردن داده‌های موقت
        _clear_otp_session(request)

        logger.info(
            f"Admin logged in: {phone} ({role})"
        )
        messages.success(
            request, 'ورود موفقیت‌آمیز بود.'
        )
        return redirect(reverse('dashboard:home'))

    return render(
        request,
        'dashboard/auth/verify_otp.html',
        {
            'masked_phone': masked_phone,
            'error': error,
        },
    )


# ═══════════════════════════════════════════════
#   ارسال مجدد کد
# ═══════════════════════════════════════════════
def resend_otp_view(request):
    """ارسال مجدد کد تایید"""
    phone = request.session.get('dashboard_otp_phone')
    if not phone:
        return redirect(reverse('dashboard:login'))

    # ─── بررسی قفل بودن ───
    if _is_login_locked(phone):
        messages.error(
            request,
            f'شماره شما موقتاً قفل شده است. '
            f'لطفاً {LOGIN_LOCKOUT_MINUTES} دقیقه '
            f'صبر کنید.'
        )
        _clear_otp_session(request)
        return redirect(reverse('dashboard:login'))

    # ─── بررسی محدودیت ارسال مجدد ───
    resend_count = request.session.get(
        'dashboard_otp_resend_count', 0
    )
    if resend_count >= MAX_RESEND_ATTEMPTS:
        messages.error(
            request,
            'تعداد ارسال‌های مجدد به حد مجاز '
            'رسیده است. لطفاً دوباره وارد شوید.'
        )
        _clear_otp_session(request)
        return redirect(reverse('dashboard:login'))

    try:
        OTPService.send_otp(
            phone=phone,
            purpose=OtpCode.Purpose.ADMIN_LOGIN,
        )
        request.session['dashboard_otp_resend_count'] = (
            resend_count + 1
        )
        # ✅ فاز ۲: شمارنده تلاش‌ها ریست نمی‌شود
        # قبلاً اینجا ریست می‌شد و قفل دور زده می‌شد
        messages.success(
            request, 'کد تایید مجدداً ارسال شد.'
        )
    except OTPException as e:
        messages.error(request, e.message)
    except Exception as e:
        logger.error(
            f"Dashboard OTP resend error: {e}",
            exc_info=True,
        )
        messages.error(
            request,
            'خطا در ارسال مجدد کد. دوباره تلاش کنید.'
        )

    return redirect(reverse('dashboard:verify_otp'))


# ═══════════════════════════════════════════════
#   خروج
# ═══════════════════════════════════════════════
def logout_view(request):
    """خروج از داشبورد"""
    phone = request.session.get(
        'dashboard_admin_phone', 'unknown'
    )
    logger.info(f"Admin logged out: {phone}")
    _clear_dashboard_session(request)
    messages.info(request, 'با موفقیت خارج شدید.')
    return redirect(reverse('dashboard:login'))


# ═══════════════════════════════════════════════
#   توابع کمکی
# ═══════════════════════════════════════════════
def _clear_otp_session(request):
    """پاک کردن داده‌های موقت فرآیند OTP"""
    keys = [
        'dashboard_otp_phone',
        'dashboard_otp_role',
        'dashboard_otp_attempts',
        'dashboard_otp_resend_count',
    ]
    for key in keys:
        request.session.pop(key, None)


def _clear_dashboard_session(request):
    """پاک کردن تمام داده‌های سشن داشبورد"""
    keys = [
        'dashboard_admin_logged_in',
        'dashboard_admin_phone',
        'dashboard_role',
        'dashboard_login_time',
        'dashboard_session_start',
        'dashboard_otp_phone',
        'dashboard_otp_role',
        'dashboard_otp_attempts',
        'dashboard_otp_resend_count',
    ]
    for key in keys:
        request.session.pop(key, None)