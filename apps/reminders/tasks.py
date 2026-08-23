"""
Celery Tasks برای یادآوری تمدید خدمات
"""
import logging
import jdatetime
from celery import shared_task
from django.utils import timezone
from django.db.models import Q

from apps.reminders.models import RenewalReminder
from apps.appointments.models import Appointment
from apps.services.models import Service
from apps.core.utils import jalali_to_key

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_renewal_reminders(self):
    """
    بررسی و ایجاد یادآوری‌های تمدید

    برای هر نوبت انجام شده (status=DONE):
    1. بررسی اینکه خدمت renewal_days > 0 دارد
    2. محاسبه تاریخ موعد تمدید
    3. ایجاد RenewalReminder اگر وجود ندارد
    """
    try:
        # دریافت نوبت‌های انجام شده که خدمتشان یادآوری تمدید دارد
        done_appointments = Appointment.objects.filter(
            status=Appointment.Status.DONE,
        ).select_related(
            'customer', 'business', 'service',
        ).filter(
            service__renewal_days__gt=0,
        )

        created_count = 0
        today = jdatetime.date.today()

        for appointment in done_appointments:
            service = appointment.service
            renewal_days = service.renewal_days

            # محاسبه تاریخ موعد تمدید
            due_date = today + jdatetime.timedelta(days=renewal_days)
            due_date_key = jalali_to_key(due_date.year, due_date.month, due_date.day)
            # بررسی وجود یادآوری قبلی
            exists = RenewalReminder.objects.filter(
                appointment=appointment,
            ).exists()

            if exists:
                continue

            # محاسبه روزهای باقی‌مانده
            days_remaining = (due_date - today).days

            # ایجاد یادآوری
            RenewalReminder.objects.create(
                business=appointment.business,
                customer=appointment.customer,
                appointment=appointment,
                service=service,
                last_service_date=appointment.date_key,
                due_date=due_date_key,
                days_remaining=days_remaining,
                reminder_sent=False,
            )

            created_count += 1

        logger.info(f"Renewal reminders created: {created_count}")
        return {'created': created_count}

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
        today = jdatetime.date.today()
        # ✅ اصلاح: jyear/jmonth/jday → year/month/day
        today_key = jalali_to_key(today.year, today.month, today.day)

        # یادآوری‌هایی که موعدشان امروز است و هنوز ارسال نشده‌اند
        due_reminders = RenewalReminder.objects.filter(
            due_date__lte=today_key,
            reminder_sent=False,
        ).select_related(
            'customer', 'business', 'service', 'appointment',
        )

        sent_count = 0
        for reminder in due_reminders:
            try:
                # ارسال نوتیفیکیشن
                from apps.notifications.services import NotificationService
                NotificationService.send(
                    user=reminder.customer,
                    type='booking_reminder',
                    title='یادآوری تمدید خدمت ⏰',
                    body=(
                        f'زمان تمدید {reminder.service.name} '
                        f'در {reminder.business.name} فرا رسیده است. '
                        f'همین حالا نوبت خود را رزرو کنید.'
                    ),
                    data={
                        'reminder_id': reminder.id,
                        'service_id': reminder.service.id,
                        'business_id': reminder.business.id,
                    },
                    channels=['in_app', 'sms'],
                )

                reminder.reminder_sent = True
                reminder.sent_date = today_key
                reminder.save(update_fields=['reminder_sent', 'sent_date'])

                sent_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to send reminder {reminder.id}: {e}"
                )

        logger.info(f"Due reminders sent: {sent_count}")
        return {'sent': sent_count}

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
        ).select_related('customer', 'service')

        updated_count = 0
        for reminder in sent_reminders:
            # بررسی رزرو جدید پس از ارسال یادآوری
            has_new = Appointment.objects.filter(
                customer=reminder.customer,
                service=reminder.service,
                status__in=[
                    Appointment.Status.RESERVED,
                    Appointment.Status.DONE,
                ],
                created_at__gt=reminder.sent_date,
            ).exists()

            if has_new:
                reminder.has_new_booking_after_send = True
                reminder.save(update_fields=['has_new_booking_after_send'])
                updated_count += 1

        logger.info(f"New booking after reminder: {updated_count}")
        return {'updated': updated_count}

    except Exception as e:
        logger.error(f"Check new booking failed: {e}")
        return {'updated': 0}