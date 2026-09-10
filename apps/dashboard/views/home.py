# apps/dashboard/views/home.py

"""
داشبورد اصلی — صفحه خوش‌آمدگویی با آمار واقعی
✅ فاز ۵: بهینه‌سازی کوئری‌ها + کش‌سازی پیشرفته
"""

import json
import logging
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from apps.dashboard.decorators import admin_login_required
from apps.dashboard.services.cache_service import DashboardCacheService


logger = logging.getLogger(__name__)


def _build_dashboard_stats():
    """
    ساخت آمار داشبورد

    ✅ فاز ۵: بهینه‌سازی‌های اعمال شده:
    1. همه کوئری‌ها در یک تابع متمرکز شده‌اند
    2. نتیجه کش می‌شود تا هر درخواست ۱۷ کوئری نزند
    3. لیست‌های اخیر با only() برای کاهش حجم داده
    4. تاریخ‌های ۷ روز اخیر با annotate برای کاهش کوئری‌ها
    """

    from apps.accounts.models import User
    from apps.appointments.models import Appointment
    from apps.businesses.models import Business
    from apps.explore.models import ExplorePost
    from apps.landing.models import ContactMessage
    from apps.payments.models import Settlement, Transaction
    from apps.portfolios.models import Portfolio
    from apps.reviews.models import Review
    from apps.support.models import SupportTicket

    seven_days_ago = timezone.now() - timedelta(days=7)

    # ─── آمار کلی (۹ کوئری aggregate) ───
    # ✅ فاز ۵: همه در یک بلوک، بدون تکرار

    users_stats = User.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        verified=Count(
            "id",
            filter=Q(is_verified=True),
        ),
        active=Count(
            "id",
            filter=Q(is_active=True),
        ),
        new_today=Count(
            "id",
            filter=Q(date_joined__date=timezone.now().date()),
        ),
    )

    businesses_stats = Business.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        approved=Count(
            "id",
            filter=Q(status="approved"),
        ),
        pending=Count(
            "id",
            filter=Q(status="pending"),
        ),
        rejected=Count(
            "id",
            filter=Q(status="rejected"),
        ),
    )

    appointments_stats = Appointment.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        reserved=Count(
            "id",
            filter=Q(status="reserved"),
        ),
        done=Count(
            "id",
            filter=Q(status="done"),
        ),
        cancelled=Count(
            "id",
            filter=Q(
                status__in=[
                    "cancelled_by_customer",
                    "cancelled_by_salon",
                ]
            ),
        ),
    )

    transactions_stats = Transaction.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        total_amount=Sum("amount"),
        blocked=Count(
            "id",
            filter=Q(status="blocked"),
        ),
        settled=Count(
            "id",
            filter=Q(status="settled"),
        ),
    )

    reviews_stats = Review.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        avg_rating=Avg("rating"),
    )

    tickets_stats = SupportTicket.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        open=Count(
            "id",
            filter=Q(status="open"),
        ),
        in_progress=Count(
            "id",
            filter=Q(status="in_progress"),
        ),
        resolved=Count(
            "id",
            filter=Q(status="resolved"),
        ),
    )

    contact_stats = ContactMessage.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        unread=Count(
            "id",
            filter=Q(is_read=False),
        ),
    )

    explore_stats = ExplorePost.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        pinned=Count(
            "id",
            filter=Q(is_pinned=True),
        ),
    )

    portfolios_stats = Portfolio.objects.filter(is_active=True).aggregate(
        total=Count("id"),
    )

    settlement_stats = Settlement.objects.filter(is_active=True).aggregate(
        total=Count("id"),
    )

    # ─── آمار ۷ روز اخیر (۳ کوئری) ───
    # ✅ فاز ۵: با annotate برای کاهش کوئری‌ها

    appointments_7days = list(
        Appointment.objects.filter(
            created_at__gte=seven_days_ago
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    transactions_7days = list(
        Transaction.objects.filter(
            created_at__gte=seven_days_ago
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(
            count=Count("id"),
            total=Sum("amount"),
        )
        .order_by("date")
    )

    users_7days = list(
        User.objects.filter(
            date_joined__gte=seven_days_ago
        )
        .annotate(date=TruncDate("date_joined"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # ─── لیست‌های اخیر (۵ کوئری با only() برای کاهش حجم داده) ───
    # ✅ فاز ۵: فقط فیلدهای لازم خوانده شوند

    recent_users = list(
        User.objects.only(
            "id",
            "phone",
            "first_name",
            "last_name",
            "avatar",
            "is_active",
            "date_joined",
        )
        .order_by("-date_joined")[:5]
    )

    recent_businesses = list(
        Business.objects.select_related(
            "owner",
            "category",
            "city",
        )
        .only(
            "id",
            "name",
            "status",
            "is_vip",
            "created_at",
            "owner__phone",
            "category__name",
            "city__name",
        )
        .order_by("-created_at")[:5]
    )

    recent_appointments = list(
        Appointment.objects.select_related(
            "customer",
            "business",
            "service",
        )
        .only(
            "id",
            "date_key",
            "status",
            "created_at",
            "customer__phone",
            "business__name",
            "service__name",
        )
        .order_by("-created_at")[:5]
    )

    recent_transactions = list(
        Transaction.objects.select_related(
            "customer",
            "business",
        )
        .only(
            "id",
            "tracking_code",
            "amount",
            "type",
            "status",
            "created_at",
            "customer__phone",
            "business__name",
        )
        .order_by("-created_at")[:5]
    )

    pending_businesses = list(
        Business.objects.select_related(
            "owner",
            "city",
        )
        .filter(status="pending")
        .only(
            "id",
            "name",
            "created_at",
            "owner__phone",
            "city__name",
        )
        .order_by("-created_at")[:5]
    )

    # ─── ساخت chart_data ───

    chart_data = {
        "appointments_labels": [
            d["date"].strftime("%m/%d")
            for d in appointments_7days
        ],
        "appointments_values": [
            d["count"]
            for d in appointments_7days
        ],
        "transactions_labels": [
            d["date"].strftime("%m/%d")
            for d in transactions_7days
        ],
        "transactions_values": [
            d["count"]
            for d in transactions_7days
        ],
        "users_labels": [
            d["date"].strftime("%m/%d")
            for d in users_7days
        ],
        "users_values": [
            d["count"]
            for d in users_7days
        ],
    }

    return {
        "users_stats": users_stats,
        "businesses_stats": businesses_stats,
        "appointments_stats": appointments_stats,
        "transactions_stats": transactions_stats,
        "reviews_stats": reviews_stats,
        "tickets_stats": tickets_stats,
        "contact_stats": contact_stats,
        "explore_stats": explore_stats,
        "portfolios_stats": portfolios_stats,
        "settlement_stats": settlement_stats,
        "chart_data_json": json.dumps(
            chart_data,
            ensure_ascii=False,
        ),
        "recent_users": recent_users,
        "recent_businesses": recent_businesses,
        "recent_appointments": recent_appointments,
        "recent_transactions": recent_transactions,
        "pending_businesses": pending_businesses,
    }


@admin_login_required
def home_view(request):
    """صفحه اصلی داشبورد با آمار"""

    role = request.session.get(
        "dashboard_role",
        "super_admin",
    )
    phone = request.session.get(
        "dashboard_admin_phone",
        "",
    )

    # ✅ فاز ۵: تلاش برای دریافت از کش
    stats = DashboardCacheService.get_dashboard_stats()

    if stats is None:
        # کش خالی است → ساخت آمار و ذخیره در کش
        try:
            stats = _build_dashboard_stats()
            DashboardCacheService.set_dashboard_stats(stats)

        except Exception as e:
            logger.error(
                f"Dashboard stats build error: {e}",
                exc_info=True,
            )

            # مقادیر پیش‌فرض در صورت خطا
            stats = {
                "users_stats": {
                    "total": 0,
                    "verified": 0,
                    "active": 0,
                    "new_today": 0,
                },
                "businesses_stats": {
                    "total": 0,
                    "approved": 0,
                    "pending": 0,
                    "rejected": 0,
                },
                "appointments_stats": {
                    "total": 0,
                    "reserved": 0,
                    "done": 0,
                    "cancelled": 0,
                },
                "transactions_stats": {
                    "total": 0,
                    "total_amount": 0,
                    "blocked": 0,
                    "settled": 0,
                },
                "reviews_stats": {
                    "total": 0,
                    "avg_rating": 0,
                },
                "tickets_stats": {
                    "total": 0,
                    "open": 0,
                    "in_progress": 0,
                    "resolved": 0,
                },
                "contact_stats": {
                    "total": 0,
                    "unread": 0,
                },
                "explore_stats": {
                    "total": 0,
                    "pinned": 0,
                },
                "portfolios_stats": {
                    "total": 0,
                },
                "settlement_stats": {
                    "total": 0,
                },
                "chart_data_json": "{}",
                "recent_users": [],
                "recent_businesses": [],
                "recent_appointments": [],
                "recent_transactions": [],
                "pending_businesses": [],
            }

    context = {
        "role": role,
        "phone": phone,
        "current_time": timezone.now(),

        # آمار
        "users_stats": stats["users_stats"],
        "businesses_stats": stats["businesses_stats"],
        "appointments_stats": stats["appointments_stats"],
        "transactions_stats": stats["transactions_stats"],
        "reviews_stats": stats["reviews_stats"],
        "tickets_stats": stats["tickets_stats"],
        "contact_stats": stats["contact_stats"],
        "explore_stats": stats["explore_stats"],
        "portfolios_stats": stats["portfolios_stats"],
        "settlement_stats": stats["settlement_stats"],

        # نمودارها
        "chart_data_json": stats["chart_data_json"],

        # لیست‌ها
        "recent_users": stats["recent_users"],
        "recent_businesses": stats["recent_businesses"],
        "recent_appointments": stats["recent_appointments"],
        "recent_transactions": stats["recent_transactions"],
        "pending_businesses": stats["pending_businesses"],
    }

    return render(
        request,
        "dashboard/home/index.html",
        context,
    )