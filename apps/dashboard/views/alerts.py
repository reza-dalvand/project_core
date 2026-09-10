# apps/dashboard/views/alerts.py
"""
✅ فاز ۹: داشبورد هشدارها
نمایش هشدارهای سیستم (کسب‌وکارهای در انتظار، تسویه‌های معوق، ...)
"""

import logging
from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.businesses.models import Business
from apps.dashboard.decorators import admin_login_required, role_required
from apps.landing.models import ContactMessage
from apps.payments.models import Settlement
from apps.support.models import SupportTicket

logger = logging.getLogger(__name__)


@admin_login_required
def alerts_view(request):
    """داشبورد هشدارها"""

    alerts = []

    # ─── کسب‌وکارهای در انتظار تایید ───
    try:
        pending_businesses_count = Business.objects.filter(
            status="pending",
            is_active=True,
        ).count()

        if pending_businesses_count > 0:
            alerts.append(
                {
                    "type": "warning",
                    "icon": "🏪",
                    "title": "کسب‌وکارهای در انتظار تایید",
                    "description": (
                        f"{pending_businesses_count} "
                        "کسب‌وکار در انتظار تایید هستند."
                    ),
                    "count": pending_businesses_count,
                    "link": "businesses_list",
                    "link_params": {"status": "pending"},
                }
            )

    except Exception as e:
        logger.error(
            f"Alerts businesses error: {e}"
        )

    # ─── تسویه‌های در انتظار پردازش ───
    try:
        pending_settlements_count = Settlement.objects.filter(
            status="pending",
            is_active=True,
        ).count()

        if pending_settlements_count > 0:
            alerts.append(
                {
                    "type": "warning",
                    "icon": "🏧",
                    "title": "تسویه‌های در انتظار",
                    "description": (
                        f"{pending_settlements_count} "
                        "تسویه در انتظار پردازش هستند."
                    ),
                    "count": pending_settlements_count,
                    "link": "settlements_list",
                    "link_params": {"status": "pending"},
                }
            )

    except Exception as e:
        logger.error(
            f"Alerts settlements error: {e}"
        )

    # ─── تیکت‌های باز ───
    try:
        open_tickets_count = SupportTicket.objects.filter(
            status="open",
            is_active=True,
        ).count()

        if open_tickets_count > 0:
            alerts.append(
                {
                    "type": "info",
                    "icon": "🎧",
                    "title": "تیکت‌های باز",
                    "description": (
                        f"{open_tickets_count} "
                        "تیکت باز در انتظار پاسخ هستند."
                    ),
                    "count": open_tickets_count,
                    "link": "tickets_list",
                    "link_params": {"status": "open"},
                }
            )

    except Exception as e:
        logger.error(
            f"Alerts tickets error: {e}"
        )

    # ─── پیام‌های تماس خوانده نشده ───
    try:
        unread_messages_count = ContactMessage.objects.filter(
            is_read=False,
            is_active=True,
        ).count()

        if unread_messages_count > 0:
            alerts.append(
                {
                    "type": "info",
                    "icon": "📨",
                    "title": "پیام‌های تماس خوانده نشده",
                    "description": (
                        f"{unread_messages_count} "
                        "پیام تماس خوانده نشده دارید."
                    ),
                    "count": unread_messages_count,
                    "link": "messages_list",
                    "link_params": {"read": "unread"},
                }
            )

    except Exception as e:
        logger.error(
            f"Alerts messages error: {e}"
        )

    # ─── نوبت‌های امروز ───
    try:
        import jdatetime

        today = jdatetime.date.today()
        today_key = (
            f"{today.year}/{today.month:02d}/{today.day:02d}"
        )

        today_appointments_count = Appointment.objects.filter(
            date_key=today_key,
            status="reserved",
            is_active=True,
        ).count()

        if today_appointments_count > 0:
            alerts.append(
                {
                    "type": "success",
                    "icon": "📅",
                    "title": "نوبت‌های امروز",
                    "description": (
                        f"{today_appointments_count} "
                        "نوبت فعال امروز دارید."
                    ),
                    "count": today_appointments_count,
                    "link": "appointments_list",
                    "link_params": {"date_filter": "today"},
                }
            )

    except Exception as e:
        logger.error(
            f"Alerts appointments error: {e}"
        )

    # ─── کسب‌وکارهای با امتیاز پایین ───
    try:
        low_rating_businesses = Business.objects.filter(
            status="approved",
            is_active=True,
            rating__lt=3.0,
            reviews_count__gte=5,
        ).count()

        if low_rating_businesses > 0:
            alerts.append(
                {
                    "type": "warning",
                    "icon": "⭐",
                    "title": "کسب‌وکارهای با امتیاز پایین",
                    "description": (
                        f"{low_rating_businesses} "
                        "کسب‌وکار با امتیاز کمتر از ۳ دارند."
                    ),
                    "count": low_rating_businesses,
                    "link": "businesses_list",
                    "link_params": {},
                }
            )

    except Exception as e:
        logger.error(
            f"Alerts low rating error: {e}"
        )

    # ─── مرتب‌سازی بر اساس اولویت ───
    priority_order = {
        "warning": 0,
        "info": 1,
        "success": 2,
    }

    alerts.sort(
        key=lambda x: priority_order.get(x["type"], 3)
    )

    # ─── context ───
    context = {
        "alerts": alerts,
        "total_alerts": len(alerts),
    }

    return render(
        request,
        "dashboard/alerts.html",
        context,
    )