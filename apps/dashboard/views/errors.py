# apps/dashboard/views/errors.py
"""
ویوهای خطای سفارشی داشبورد
✅ فاز ۱: تمپلیت‌های مستقل از base.html
خطاها نباید به سشن یا ساختار داشبورد وابسته باشند
"""
from django.shortcuts import render


def error_403(request, exception=None):
    """دسترسی غیرمجاز"""
    return render(
        request,
        'dashboard/errors/403.html',
        status=403,
    )


def error_404(request, exception=None):
    """صفحه یافت نشد"""
    return render(
        request,
        'dashboard/errors/404.html',
        status=404,
    )


def error_500(request):
    """خطای داخلی سرور"""
    return render(
        request,
        'dashboard/errors/500.html',
        status=500,
    )