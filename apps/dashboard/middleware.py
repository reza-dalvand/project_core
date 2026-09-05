# apps/dashboard/middleware.py
"""
میدلور مدیریت سشن داشبورد ادمین
✅ باگ‌فیکس: حذف استفاده نادرست از timezone.datetime
"""
import logging
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta

logger = logging.getLogger(__name__)


class DashboardSessionMiddleware:
    """مدیریت انقضای سشن داشبورد"""
    SESSION_TIMEOUT_MINUTES = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.session.get('dashboard_admin_logged_in'):
            login_time_str = request.session.get('dashboard_login_time')
            if login_time_str:
                try:
                    # ✅ FIX: قبلاً:
                    #   timezone.datetime.fromisoformat(login_time_str)
                    # که اصلاً وجود خارجی ندارد و خطا می‌دهد
                    login_time = parse_datetime(login_time_str)

                    if login_time and timezone.is_naive(login_time):
                        login_time = timezone.make_aware(login_time)

                    if login_time:
                        elapsed = timezone.now() - login_time
                        if elapsed > timedelta(
                            minutes=self.SESSION_TIMEOUT_MINUTES
                        ):
                            logger.info(
                                "Dashboard session expired for "
                                f"{request.session.get('dashboard_admin_phone', 'unknown')}"
                            )
                            keys = [
                                'dashboard_admin_logged_in',
                                'dashboard_admin_phone',
                                'dashboard_role',
                                'dashboard_login_time',
                            ]
                            for key in keys:
                                request.session.pop(key, None)
                            return redirect(reverse('dashboard:login'))

                except (ValueError, TypeError):
                    pass

            # تمدید سشن با هر درخواست
            request.session['dashboard_login_time'] = (
                timezone.now().isoformat()
            )

        return self.get_response(request)