"""
سرویس‌های یادآوری تمدید خدمت

✅ هدف:
- محاسبه درست تاریخ موعد تمدید بر اساس تاریخ نوبت/خدمت
- create یا update رکورد RenewalReminder
- جلوگیری از stale شدن days_remaining
"""

import logging

import jdatetime
from django.utils import timezone

from apps.core.utils import jalali_to_key
from apps.reminders.models import RenewalReminder

logger = logging.getLogger(__name__)


def get_today_jalali():
    """
    تاریخ امروز جلالی بر اساس timezone پروژه.
    """
    now_local = timezone.localtime(timezone.now())
    return jdatetime.date.fromgregorian(date=now_local.date())


def _appointment_service_jalali_date(appointment):
    """
    تاریخ جلالی سرویس/نوبت.

    ✅ مبنای اصلی: jy/jm/jd خود نوبت
    دلیل:
    - done_at ممکن است زمان تایید باشد، نه زمان واقعی خدمت
    - در نوبت‌های اعتمادی که چند روز بعد auto-confirm می‌شوند، done_at گمراه‌کننده است
    """
    try:
        return jdatetime.date(
            int(appointment.jy),
            int(appointment.jm),
            int(appointment.jd),
        )
    except (ValueError, TypeError, AttributeError):
        # fallback امن
        return get_today_jalali()


def calculate_reminder_dates(appointment):
    """
    محاسبه مقادیر تاریخ یادآوری برای یک نوبت.

    Returns:
        dict | None
        اگر خدمت renewal_days <= 0 باشد، None برمی‌گرداند.
    """
    service = getattr(appointment, "service", None)
    if service is None:
        return None

    renewal_days = getattr(service, "renewal_days", 0) or 0
    if renewal_days <= 0:
        return None

    service_date = _appointment_service_jalali_date(appointment)
    today = get_today_jalali()

    due_date = service_date + jdatetime.timedelta(days=int(renewal_days))

    return {
        "last_service_date": jalali_to_key(
            service_date.year,
            service_date.month,
            service_date.day,
        ),
        "due_date": jalali_to_key(
            due_date.year,
            due_date.month,
            due_date.day,
        ),
        "days_remaining": (due_date - today).days,
    }


def ensure_renewal_reminder_for_appointment(appointment, existing_reminder=None):
    """
    مطمئن شود برای یک نوبت انجام‌شده، یادآوری تمدید وجود دارد و مقادیرش درست است.

    Args:
        appointment: Appointment instance
        existing_reminder: در صورتی که از قبل reminder مربوطه را load کرده‌ایم

    Returns:
        tuple: (reminder, status)
        status یکی از:
          - created
          - updated
          - unchanged
          - skipped
    """
    dates = calculate_reminder_dates(appointment)
    if dates is None:
        return None, "skipped"

    reminder = existing_reminder

    # safety: اگر reminder مربوط به appointment دیگری بود، نادیده بگیر
    if reminder is not None and reminder.appointment_id != appointment.id:
        reminder = None

    if reminder is None:
        reminder = (
            RenewalReminder.objects.filter(appointment=appointment)
            .order_by("id")
            .first()
        )

    if reminder is not None:
        update_fields = []

        # بروزرسانی مقادیر تاریخ
        for field, value in dates.items():
            if getattr(reminder, field) != value:
                setattr(reminder, field, value)
                update_fields.append(field)

        # بروزرسانی روابط در صورت نیاز
        for field, related in (
            ("business", appointment.business),
            ("customer", appointment.customer),
            ("service", appointment.service),
        ):
            if related is None:
                continue

            if getattr(reminder, f"{field}_id") != related.id:
                setattr(reminder, field, related)
                update_fields.append(field)

        if update_fields:
            # اگر مدل updated_at دارد، آن را هم include کن
            if "updated_at" not in update_fields:
                update_fields.append("updated_at")

            reminder.save(update_fields=list(dict.fromkeys(update_fields)))
            return reminder, "updated"

        return reminder, "unchanged"

    reminder = RenewalReminder.objects.create(
        business=appointment.business,
        customer=appointment.customer,
        appointment=appointment,
        service=appointment.service,
        reminder_sent=False,
        **dates,
    )

    return reminder, "created"