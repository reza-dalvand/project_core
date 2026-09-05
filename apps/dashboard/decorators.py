# apps/dashboard/decorators.py
"""
دکوراتورهای احراز هویت داشبورد ادمین
✅ فاز ۲: افزودن لاگ امنیتی
✅ فاز ۲: بررسی مجدد اعتبار کاربر
✅ فاز ۱: فیکس بررسی کامل سشن
"""
import logging
from functools import wraps
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()

_dashboard_settings = getattr(
    settings, 'DASHBOARD_SETTINGS', {}
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


def _check_ip_restriction(request):
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


def admin_login_required(view_func):
    """دکوراتور اجباری: کاربر باید وارد داشبورد شده باشد"""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        # ─── ۰. بررسی محدودسازی بر اساس نقش در دکوراتور ───
        if not _check_ip_restriction(request):
            return redirect(reverse('dashboard:login'))

        # ─── ۱. بررسی ورود اولیه ───
        if not request.session.get('dashboard_admin_logged_in'):
            return redirect(reverse('dashboard:login'))

        # ─── ۲. بررسی وجود شماره تلفن در سشن ───
        phone = request.session.get(
            'dashboard_admin_phone'
        )
        if not phone:
            _clear_dashboard_session(request)
            return redirect(reverse('dashboard:login'))

        # ─── ۳. بررسی مجدد اعتبار کاربر ───
        try:
            user = User.objects.filter(
                phone=phone,
                is_staff=True,
                is_active=True,
            ).first()
        except Exception:
            _clear_dashboard_session(request)
            return redirect(reverse('dashboard:login'))

        if not user:
            logger.warning(
                f"Dashboard access denied: "
                f"phone={phone} — user no longer valid"
            )
            _clear_dashboard_session(request)
            return redirect(reverse('dashboard:login'))

        # ─── ۴. بررسی پروفایل ادمین ───
        try:
            admin_profile = getattr(
                user, 'admin_profile', None
            )
            if admin_profile and not admin_profile.is_active:
                logger.warning(
                    f"Dashboard access denied: "
                    f"phone={phone} — admin_profile inactive"
                )
                _clear_dashboard_session(request)
                return redirect(reverse('dashboard:login'))
        except Exception:
            _clear_dashboard_session(request)
            return redirect(reverse('dashboard:login'))

        return view_func(request, *args, **kwargs)

    return _wrapped


def super_admin_required(view_func):
    """فقط سوپر ادمین"""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get(
            'dashboard_admin_logged_in'
        ):
            return redirect(reverse('dashboard:login'))

        role = request.session.get('dashboard_role')
        if role != 'super_admin':
            # ✅ فاز ۲: لاگ امنیتی
            logger.warning(
                f"Dashboard super_admin access denied: "
                f"phone={request.session.get('dashboard_admin_phone', 'unknown')} "
                f"role={role}"
            )
            return redirect(reverse('dashboard:home'))

        return view_func(request, *args, **kwargs)

    return _wrapped


def role_required(*allowed_roles):
    """فقط نقش‌های مشخص‌شده دسترسی دارند"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.session.get(
                'dashboard_admin_logged_in'
            ):
                return redirect(reverse('dashboard:login'))

            role = request.session.get('dashboard_role', '')

            # سوپر ادمین همیشه دسترسی دارد
            if role == 'super_admin':
                return view_func(request, *args, **kwargs)

            if role not in allowed_roles:
                # ✅ فاز ۲: لاگ امنیتی دسترسی ناموفق
                logger.warning(
                    f"Dashboard access denied: "
                    f"phone={request.session.get('dashboard_admin_phone', 'unknown')} "
                    f"role={role} "
                    f"required_roles={list(allowed_roles)}"
                )
                from django.contrib import messages
                messages.error(
                    request,
                    'شما به این بخش دسترسی ندارید.'
                )
                return redirect(reverse('dashboard:home'))

            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator