"""
دکوراتورهای احراز هویت داشبورد ادمین
"""
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse


# apps/dashboard/decorators.py
from django.contrib.auth import get_user_model

User = get_user_model()

def admin_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get('dashboard_admin_logged_in'):
            return redirect(reverse('dashboard:login'))

        # ✅ بررسی مجدد اعتبار کاربر
        phone = request.session.get('dashboard_admin_phone')
        if phone:
            user = User.objects.filter(
                phone=phone, is_staff=True, is_active=True
            ).first()
            if not user:
                # کاربر غیرفعال شده → خروج اجباری
                _clear_dashboard_session(request)
                return redirect(reverse('dashboard:login'))

            # بررسی AdminUser
            admin_profile = getattr(user, 'admin_profile', None)
            if admin_profile and not admin_profile.is_active:
                _clear_dashboard_session(request)
                return redirect(reverse('dashboard:login'))

        return view_func(request, *args, **kwargs)
    return _wrapped


def _clear_dashboard_session(request):
    """پاک کردن تمام داده‌های سشن داشبورد"""
    keys_to_remove = [
        'dashboard_admin_logged_in',
        'dashboard_admin_phone',
        'dashboard_role',
        'dashboard_login_time',
    ]
    for key in keys_to_remove:
        request.session.pop(key, None)


def super_admin_required(view_func):
    """فقط سوپر ادمین"""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get('dashboard_admin_logged_in'):
            return redirect(reverse('dashboard:login'))
        if request.session.get('dashboard_role') != 'super_admin':
            return redirect(reverse('dashboard:home'))
        return view_func(request, *args, **kwargs)
    return _wrapped


def role_required(*allowed_roles):
    """فقط نقش‌های مشخص‌شده دسترسی دارن"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.session.get('dashboard_admin_logged_in'):
                return redirect(reverse('dashboard:login'))

            role = request.session.get('dashboard_role', '')
            if role == 'super_admin':
                return view_func(request, *args, **kwargs)

            if role not in allowed_roles:
                from django.contrib import messages
                messages.error(request, 'شما به این بخش دسترسی ندارید.')
                return redirect(reverse('dashboard:home'))

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator