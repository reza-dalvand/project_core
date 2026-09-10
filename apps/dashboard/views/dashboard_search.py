# apps/dashboard/views/dashboard_search.py
"""
✅ فاز ۹: جستجوی سراسری در داشبورد
یک جستجو برای همه بخش‌ها (کاربران، کسب‌وکارها، تراکنش‌ها، ...)
"""

import logging

from django.db.models import Q
from django.shortcuts import render

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.businesses.models import Business
from apps.dashboard.decorators import admin_login_required
from apps.payments.models import Transaction
from apps.support.models import SupportTicket

logger = logging.getLogger(__name__)


@admin_login_required
def dashboard_search_view(request):
    """جستجوی سراسری در داشبورد"""

    query = request.GET.get("q", "").strip()

    results = {
        "users": [],
        "businesses": [],
        "transactions": [],
        "appointments": [],
        "tickets": [],
    }

    total_results = 0

    if query and len(query) >= 2:

        # ─── جستجو در کاربران ───
        try:
            users = User.objects.filter(
                Q(phone__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(national_id__icontains=query)
            ).only(
                "id",
                "phone",
                "first_name",
                "last_name",
                "is_active",
            )[:10]

            results["users"] = list(users)
            total_results += len(results["users"])

        except Exception as e:
            logger.error(
                f"Search users error: {e}"
            )

        # ─── جستجو در کسب‌وکارها ───
        try:
            businesses = Business.objects.filter(
                Q(name__icontains=query)
                | Q(address__icontains=query)
                | Q(owner__phone__icontains=query)
            ).select_related(
                "owner",
                "city",
            ).only(
                "id",
                "name",
                "status",
                "rating",
                "owner__phone",
                "city__name",
            )[:10]

            results["businesses"] = list(businesses)
            total_results += len(results["businesses"])

        except Exception as e:
            logger.error(
                f"Search businesses error: {e}"
            )

        # ─── جستجو در تراکنش‌ها ───
        try:
            transactions = Transaction.objects.filter(
                Q(tracking_code__icontains=query)
                | Q(ref_number__icontains=query)
                | Q(customer__phone__icontains=query)
                | Q(business__name__icontains=query)
            ).select_related(
                "customer",
                "business",
            ).only(
                "id",
                "tracking_code",
                "amount",
                "status",
                "customer__phone",
                "business__name",
            )[:10]

            results["transactions"] = list(transactions)
            total_results += len(results["transactions"])

        except Exception as e:
            logger.error(
                f"Search transactions error: {e}"
            )

        # ─── جستجو در نوبت‌ها ───
        try:
            appointments = Appointment.objects.filter(
                Q(customer__phone__icontains=query)
                | Q(business__name__icontains=query)
                | Q(service__name__icontains=query)
                | Q(verification_code__icontains=query)
            ).select_related(
                "customer",
                "business",
                "service",
            ).only(
                "id",
                "date_key",
                "time_slot",
                "status",
                "customer__phone",
                "business__name",
                "service__name",
            )[:10]

            results["appointments"] = list(appointments)
            total_results += len(results["appointments"])

        except Exception as e:
            logger.error(
                f"Search appointments error: {e}"
            )

        # ─── جستجو در تیکت‌ها ───
        try:
            tickets = SupportTicket.objects.filter(
                Q(subject__icontains=query)
                | Q(message__icontains=query)
                | Q(user__phone__icontains=query)
            ).select_related(
                "user",
            ).only(
                "id",
                "subject",
                "status",
                "priority",
                "user__phone",
            )[:10]

            results["tickets"] = list(tickets)
            total_results += len(results["tickets"])

        except Exception as e:
            logger.error(
                f"Search tickets error: {e}"
            )

    # ─── context ───
    context = {
        "query": query,
        "results": results,
        "total_results": total_results,
    }

    return render(
        request,
        "dashboard/dashboard_search.html",
        context,
    )