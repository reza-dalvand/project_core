"""
Permissionهای سفارشی برای کاربران
"""
from rest_framework import permissions


class IsNotSuspended(permissions.BasePermission):
    """
    کاربر تعلیق‌شده نباید به APIها دسترسی داشته باشد.
    فقط APIهای logout و support مجاز هستند.
    """
    message = 'حساب کاربری شما به دلیل تخلف تعلیق شده است. لطفاً با پشتیبانی تماس بگیرید.'
    code = 'ACCOUNT_SUSPENDED'

    # endpointهایی که کاربر تعلیق‌شده هم می‌تواند استفاده کند
    ALLOWED_URLS = [
        '/accounts/auth/logout/',
        '/accounts/auth/token/refresh/',
        '/support/tickets/',  # ارسال تیکت
        '/support/tickets/create/',
    ]

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True  # AllowAny endpoints

        # اگر کاربر تعلیق نشده، اجازه بده
        if not request.user.is_suspended:
            return True

        # اگر endpoint مجاز است، اجازه بده
        request_path = request.path
        for allowed_url in self.ALLOWED_URLS:
            if request_path.startswith(allowed_url):
                return True

        return False