# apps/dashboard/middleware.py
"""
میدلور مدیریت سشن داشبورد ادمین
✅ فاز ۲: افزودن حداکثر عمر مطلق سشن
✅ فاز ۱: فیکس انقضای سشن با فرمت نامعتبر
"""
import logging
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta

logger = logging.getLogger(__name__)


class DashboardSessionMiddleware:
    """مدیریت انقضای سشن داشبورد"""

    def __init__(self, get_response):
        self.get_response = get_response
        # ✅ فاز ۲: خواندن از تنظیمات به جای هاردکد
        dashboard_settings = getattr(
            settings, 'DASHBOARD_SETTINGS', {}
        )
        self.session_timeout_minutes = (
            dashboard_settings.get('SESSION_TIMEOUT_MINUTES', 60)
        )
        self.absolute_timeout_hours = (
            dashboard_settings.get(
                'ABSOLUTE_SESSION_TIMEOUT_HOURS', 8
            )
        )

    def __call__(self, request):
        if request.session.get('dashboard_admin_logged_in'):
            # ─── بررسی حداکثر عمر مطلق سشن ───
            # ✅ فاز ۲: حتی اگر کاربر فعال باشد،
            # بعد از ۸ ساعت باید دوباره وارد شود
            absolute_start = request.session.get(
                'dashboard_session_start'
            )
            if absolute_start:
                try:
                    start_time = parse_datetime(absolute_start)
                    if start_time is not None:
                        if timezone.is_naive(start_time):
                            start_time = timezone.make_aware(
                                start_time
                            )
                        total_elapsed = (
                            timezone.now() - start_time
                        )
                        if total_elapsed > timedelta(
                            hours=self.absolute_timeout_hours
                        ):
                            logger.info(
                                "Dashboard session absolute "
                                "timeout reached for "
                                f"{request.session.get('dashboard_admin_phone', 'unknown')}"
                            )
                            self._clear_session(request)
                            return redirect(
                                reverse('dashboard:login')
                            )
                except (ValueError, TypeError, OverflowError):
                    self._clear_session(request)
                    return redirect(
                        reverse('dashboard:login')
                    )

            # ─── بررسی انقضای سشن غیرفعال ───
            login_time_str = request.session.get(
                'dashboard_login_time'
            )
            if login_time_str:
                try:
                    login_time = parse_datetime(login_time_str)
                    if login_time is None:
                        logger.warning(
                            "Dashboard session has invalid "
                            f"login_time format: "
                            f"'{login_time_str}' — "
                            "clearing session"
                        )
                        self._clear_session(request)
                        return redirect(
                            reverse('dashboard:login')
                        )

                    if timezone.is_naive(login_time):
                        login_time = timezone.make_aware(
                            login_time
                        )

                    elapsed = timezone.now() - login_time
                    if elapsed > timedelta(
                        minutes=self.session_timeout_minutes
                    ):
                        logger.info(
                            "Dashboard session expired for "
                            f"{request.session.get('dashboard_admin_phone', 'unknown')}"
                        )
                        self._clear_session(request)
                        return redirect(
                            reverse('dashboard:login')
                        )

                except (ValueError, TypeError, OverflowError) as e:
                    logger.warning(
                        f"Dashboard session login_time "
                        f"parse error: {e} "
                        "— clearing session"
                    )
                    self._clear_session(request)
                    return redirect(
                        reverse('dashboard:login')
                    )

            # تمدید سشن غیرفعال با هر درخواست
            request.session['dashboard_login_time'] = (
                timezone.now().isoformat()
            )

        return self.get_response(request)

    @staticmethod
    def _clear_session(request):
        """پاک کردن تمام کلیدهای سشن داشبورد"""
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