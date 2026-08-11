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
    tomorrow_key = f'{tomorrow.jyear}/{tomorrow.jmonth:02d}/{tomorrow.jday:02d}'

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
    today_key = f'{today.jyear}/{today.jmonth:02d}/{today.jday:02d}'

    appointments = Appointment.objects.filter(
        date_key=today_key,
        status=Appointment.Status.RESERVED,
        reminder_sent=False,
    ).select_related('customer', 'business', 'service')

    sent_count = 0
    for appointment in appointments:
        try:
            # بررسی فاصله زمانی
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


@shared_task(bind=True, max_retries=3)
def auto_settle_completed_appointments(self):
    """
    تسویه خودکار نوبت‌های انجام شده
    هر ۱ ساعت اجرا می‌شود
    """
    from apps.appointments.models import Appointment
    from apps.payments.models import Transaction
    from apps.payments.services.payment_service import PaymentService

    try:
        # نوبت‌های انجام شده با بیعانه پرداخت شده
        appointments = Appointment.objects.filter(
            status=Appointment.Status.DONE,
            is_verified=True,
        ).select_related('business', 'service').prefetch_related(
            'transactions',
        )

        processed = 0
        for appointment in appointments:
            # بررسی تراکنش‌های بیعانه
            for tx in appointment.transactions.all():
                if (
                    tx.type == Transaction.Type.DEPOSIT and
                    tx.status == Transaction.Status.BLOCKED
                ):
                    try:
                        # تغییر وضعیت به SETTLING
                        tx.status = Transaction.Status.SETTLING
                        tx.estimated_settlement = timezone.now() + timedelta(days=1)
                        tx.save(update_fields=['status', 'estimated_settlement'])

                        processed += 1
                    except Exception as e:
                        logger.error(
                            f"Auto-settle failed for appointment {appointment.id}: {e}"
                        )

        logger.info(f"Auto-settle completed: {processed} transactions processed")
        return {'processed': processed}

    except Exception as exc:
        logger.error(f"Auto-settle task failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def process_pending_settlements(self):
    """
    پردازش تسویه‌های در انتظار (خودکار)
    هر ۶ ساعت اجرا می‌شود
    """
    from apps.payments.models import Settlement
    from apps.payments.services.payment_service import PaymentService

    try:
        settlements = Settlement.objects.filter(
            status=Settlement.Status.PENDING,
            created_at__lte=timezone.now() - timedelta(hours=24),
        )

        processed = 0
        for settlement in settlements:
            try:
                PaymentService.process_settlement(settlement)
                processed += 1
            except Exception as e:
                logger.error(
                    f"Auto-process settlement {settlement.id} failed: {e}"
                )

        logger.info(f"Auto-process settlements: {processed} processed")
        return {'processed': processed}

    except Exception as exc:
        logger.error(f"Process settlements task failed: {exc}")
        raise self.retry(exc=exc, countdown=600)


@shared_task
def check_expired_pending_transactions():
    """
    بررسی تراکنش‌های PENDING که بیش از ۳۰ دقیقه گذشته
    """
    from apps.payments.models import Transaction

    threshold = timezone.now() - timedelta(minutes=30)

    expired = Transaction.objects.filter(
        status=Transaction.Status.FAILED,
        created_at__lt=threshold,
    )

    count = expired.count()

    if count > 0:
        logger.info(f"Found {count} expired pending transactions")

    return {'expired': count}


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