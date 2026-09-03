"""
دکوراتورهای احراز هویت داشبورد ادمین
"""
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse


def admin_login_required(view_func):
    """
    دکوراتور برای محافظت از صفحات داشبورد
    فقط کاربرانی که در سشن ادمین لاگین کرده‌اند دسترسی دارند
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get('dashboard_admin_logged_in'):
            return redirect(reverse('dashboard:login'))
        return view_func(request, *args, **kwargs)
    return _wrapped


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