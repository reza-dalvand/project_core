"""
Celery Tasks برای یادآوری تمدید خدمات

✅ اصلاحات:
- check_renewal_reminders حالا رکوردهای موجود را هم update می‌کند
- تاریخ موعد بر اساس تاریخ نوبت/خدمت محاسبه می‌شود، نه today تسک
- days_remaining در دیتابیس هم بروزرسانی می‌شود
"""

import logging
from datetime import datetime

import jdatetime
from celery import shared_task
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.core.utils import jalali_to_key
from apps.reminders.models import RenewalReminder
from apps.reminders.services import (
    ensure_renewal_reminder_for_appointment,
    get_today_jalali,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_renewal_reminders(self):
    """
    بررسی و ایجاد/بروزرسانی یادآوری‌های تمدید

    برای هر نوبت انجام شده (status=DONE):
    1. بررسی اینکه خدمت renewal_days > 0 دارد
    2. محاسبه تاریخ موعد تمدید بر اساس تاریخ نوبت
    3. ایجاد RenewalReminder اگر وجود ندارد
    4. بروزرسانی RenewalReminder اگر وجود دارد ولی مقادیرش قدیمی/غلط است
    """
    try:
        done_appointments = list(
            Appointment.objects.filter(
                status=Appointment.Status.DONE,
            )
            .select_related(
                "customer",
                "business",
                "service",
            )
            .filter(
                service__renewal_days__gt=0,
            )
        )

        created_count = 0
        updated_count = 0
        unchanged_count = 0
        skipped_count = 0

        if done_appointments:
            appointment_ids = [appointment.id for appointment in done_appointments]

            existing_reminders = {
                reminder.appointment_id: reminder
                for reminder in RenewalReminder.objects.filter(
                    appointment_id__in=appointment_ids
                )
            }

            for appointment in done_appointments:
                _, status = ensure_renewal_reminder_for_appointment(
                    appointment=appointment,
                    existing_reminder=existing_reminders.get(appointment.id),
                )

                if status == "created":
                    created_count += 1
                elif status == "updated":
                    updated_count += 1
                elif status == "unchanged":
                    unchanged_count += 1
                elif status == "skipped":
                    skipped_count += 1

        logger.info(
            "Renewal reminders checked — "
            f"created: {created_count}, "
            f"updated: {updated_count}, "
            f"unchanged: {unchanged_count}, "
            f"skipped: {skipped_count}"
        )

        return {
            "created": created_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
            "skipped": skipped_count,
        }

    except Exception as exc:
        logger.error(f"Renewal reminder check failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def send_due_reminders(self):
    """
    ارسال یادآوری‌هایی که موعدشان فرا رسیده

    هر روز ۸ صبح اجرا می‌شود
    """
    try:
        today = get_today_jalali()
        today_key = jalali_to_key(today.year, today.month, today.day)

        # یادآوری‌هایی که موعدشان امروز یا گذشته است و هنوز ارسال نشده‌اند
        due_reminders = RenewalReminder.objects.filter(
            due_date__lte=today_key,
            reminder_sent=False,
        ).select_related(
            "customer",
            "business",
            "service",
            "appointment",
        )

        sent_count = 0

        for reminder in due_reminders:
            try:
                # ارسال نوتیفیکیشن
                from apps.notifications.services import NotificationService

                NotificationService.send(
                    user=reminder.customer,
                    type="booking_reminder",
                    title="یادآوری تمدید خدمت ⏰",
                    body=(
                        f"زمان تمدید {reminder.service.name} "
                        f"در {reminder.business.name} فرا رسیده است. "
                        f"همین حالا نوبت خود را رزرو کنید."
                    ),
                    data={
                        "reminder_id": reminder.id,
                        "service_id": reminder.service.id,
                        "business_id": reminder.business.id,
                    },
                    channels=["in_app", "sms"],
                )

                reminder.reminder_sent = True
                reminder.sent_date = today_key
                reminder.save(update_fields=["reminder_sent", "sent_date"])

                sent_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to send reminder {reminder.id}: {e}"
                )

        logger.info(f"Due reminders sent: {sent_count}")
        return {"sent": sent_count}

    except Exception as exc:
        logger.error(f"Send due reminders failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task
def check_new_booking_after_reminder():
    """
    بررسی اینکه آیا کاربر پس از ارسال یادآوری، رزرو جدیدی داشته است
    """
    try:
        sent_reminders = RenewalReminder.objects.filter(
            reminder_sent=True,
            has_new_booking_after_send=False,
        ).select_related("customer", "service")

        updated_count = 0

        for reminder in sent_reminders:
            if not reminder.sent_date:
                continue

            try:
                parts = reminder.sent_date.split("/")
                jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
                gregorian_date = jdatetime.date(jy, jm, jd).togregorian()
                # شروع روز ارسال (ساعت ۰۰:۰۰)
                sent_datetime = timezone.make_aware(
                    datetime.combine(gregorian_date, datetime.min.time())
                )
            except (ValueError, IndexError):
                logger.warning(
                    f"Invalid sent_date format for reminder {reminder.id}: "
                    f"'{reminder.sent_date}'"
                )
                continue

            # بررسی رزرو جدید پس از ارسال یادآوری
            has_new = Appointment.objects.filter(
                customer=reminder.customer,
                service=reminder.service,
                status__in=[
                    Appointment.Status.RESERVED,
                    Appointment.Status.DONE,
                ],
                created_at__gt=sent_datetime,
            ).exists()

            if has_new:
                reminder.has_new_booking_after_send = True
                reminder.save(update_fields=["has_new_booking_after_send"])
                updated_count += 1

        logger.info(f"New booking after reminder: {updated_count}")
        return {"updated": updated_count}

    except Exception as e:
        logger.error(f"Check new booking failed: {e}")
        return {"updated": 0}