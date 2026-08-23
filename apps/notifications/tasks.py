"""
Celery Tasks برای نوتیفیکیشن‌ها
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_booking_reminders(self):
    """ارسال یادآوری نوبت‌های فردا"""
    from apps.appointments.models import Appointment
    from apps.notifications.services import NotificationService
    import jdatetime

    tomorrow = jdatetime.date.today() + jdatetime.timedelta(days=1)
    tomorrow_key = f'{tomorrow.year}/{tomorrow.month:02d}/{tomorrow.day:02d}'

    appointments = Appointment.objects.filter(
        date_key=tomorrow_key,
        status=Appointment.Status.RESERVED,
        reminder_sent=False,
    ).select_related('customer', 'business', 'service')

    sent_count = 0
    for appointment in appointments:
        try:
            NotificationService.send_booking_reminder(appointment)
            appointment.reminder_sent = True
            appointment.reminder_sent_at = timezone.now()
            appointment.save(update_fields=[
                'reminder_sent', 'reminder_sent_at',
            ])
            sent_count += 1
        except Exception as e:
            logger.error(f"Reminder failed for appointment {appointment.id}: {e}")

    logger.info(f"Booking reminders sent: {sent_count}")
    return {'sent': sent_count}


@shared_task(bind=True, max_retries=3)
def send_same_day_reminders(self):
    """ارسال یادآوری نوبت‌های امروز (۲ ساعت قبل)"""
    from apps.appointments.models import Appointment
    from apps.notifications.services import NotificationService
    import jdatetime
    from datetime import datetime

    now = timezone.now()
    today = jdatetime.date.today()
    today_key = f'{today.year}/{today.month:02d}/{today.day:02d}'

    appointments = Appointment.objects.filter(
        date_key=today_key,
        status=Appointment.Status.RESERVED,
        reminder_sent=False,
    ).select_related('customer', 'business', 'service')

    sent_count = 0
    for appointment in appointments:
        try:
            apt_time = datetime.combine(
                datetime.today(), appointment.time_slot
            )
            apt_time = timezone.make_aware(apt_time)
            hours_until = (apt_time - now).total_seconds() / 3600

            if 0 < hours_until <= 2:
                NotificationService.send(
                    user=appointment.customer,
                    type='booking_reminder',
                    title='یادآوری نوبت امروز ⏰',
                    body=(
                        f'تا {int(hours_until)} ساعت دیگر نوبت '
                        f'{appointment.service.name} '
                        f'در {appointment.business.name} دارید.'
                    ),
                    data={'appointment_id': appointment.id},
                    channels=['in_app', 'sms'],
                )
                appointment.reminder_sent = True
                appointment.reminder_sent_at = timezone.now()
                appointment.save(update_fields=[
                    'reminder_sent', 'reminder_sent_at',
                ])
                sent_count += 1
        except Exception as e:
            logger.error(f"Same-day reminder failed: {e}")

    return {'sent': sent_count}

@shared_task
def verify_unconfirmed_payments():
    """
    بررسی و تایید پرداخت‌های تایید نشده
    هر ۵ دقیقه اجرا می‌شود
    """
    from apps.payments.models import Transaction
    from shared.payment import get_payment_gateway

    transactions = Transaction.objects.filter(
        status=Transaction.Status.BLOCKED,
        gateway_transaction_id__isnull=False,
        created_at__gte=timezone.now() - timedelta(hours=2),
    ).select_related('appointment')

    # ✅ اصلاح: فیلتر رشته خالی
    # فیلد gateway_transaction_id دارای blank=True, default='' است
    # رکوردهایی که هنوز به درگاه نرفته‌اند مقدار '' دارند
    transactions = transactions.exclude(gateway_transaction_id='')

    verified = 0
    for tx in transactions:
        try:
            gateway = get_payment_gateway()
            result = gateway.verify_payment(
                track_id=tx.gateway_transaction_id,
                amount_toman=tx.amount,
            )
            if result.success:
                tx.status = Transaction.Status.BLOCKED
                tx.ref_number = result.ref_number
                tx.save(update_fields=['status', 'ref_number'])
                verified += 1
        except Exception as e:
            logger.debug(f"Payment {tx.id} not yet confirmed: {e}")

    if verified > 0:
        logger.info(f"Verified {verified} unconfirmed payments")
    return {'verified': verified}


@shared_task
def cleanup_old_notifications():
    """حذف اعلان‌های قدیمی (۹۰ روز)"""
    from apps.notifications.models import Notification

    cutoff = timezone.now() - timedelta(days=90)
    total_deleted = 0
    batch_size = 1000

    while True:
        ids_to_delete = list(
            Notification.objects.filter(
                created_at__lt=cutoff,
                is_read=True,
            ).values_list('id', flat=True)[:batch_size]
        )
        if not ids_to_delete:
            break
        deleted_count, _ = Notification.objects.filter(
            id__in=ids_to_delete
        ).delete()
        total_deleted += deleted_count
        if len(ids_to_delete) < batch_size:
            break

    logger.info(f"Cleaned up {total_deleted} old notifications")
    return {'deleted': total_deleted}


@shared_task
def cleanup_old_otp_codes():
    """حذف کدهای OTP قدیمی (۲۴ ساعت)"""
    from apps.accounts.models import OtpCode

    cutoff = timezone.now() - timedelta(hours=24)
    total_deleted = 0
    batch_size = 2000

    while True:
        ids = list(
            OtpCode.objects.filter(
                created_at__lt=cutoff,
                is_used=True,
            ).values_list('id', flat=True)[:batch_size]
        )
        if not ids:
            break
        deleted, _ = OtpCode.objects.filter(id__in=ids).delete()
        total_deleted += deleted
        if len(ids) < batch_size:
            break

    logger.info(f"Cleaned up {total_deleted} old OTP codes")
    return {'deleted': total_deleted}