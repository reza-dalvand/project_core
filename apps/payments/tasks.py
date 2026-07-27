"""
وظایف Celery برای پردازش‌های پس‌زمینه
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def auto_settle_completed_appointments(self):
    """
    تسویه خودکار نوبت‌های انجام شده
    هر ۱ ساعت اجرا می‌شود
    """
    from apps.payments.services.settlement_service import SettlementService

    try:
        processed = SettlementService.auto_settle_completed_appointments()
        logger.info(f"Auto-settle task completed: {processed} transactions")
        return {'processed': processed}
    except Exception as exc:
        logger.error(f"Auto-settle task failed: {exc}")
        raise self.retry(exc=exc, countdown=300)  # retry after 5 minutes


@shared_task(bind=True, max_retries=3)
def process_pending_settlements(self):
    """
    پردازش تسویه‌های در انتظار (خودکار)
    هر ۶ ساعت اجرا می‌شود
    """
    from apps.payments.models import Settlement
    from apps.payments.services.settlement_service import SettlementService

    try:
        settlements = Settlement.objects.filter(
            status=Settlement.Status.PENDING,
            requested_at__lte=timezone.now() - timezone.timedelta(hours=24),
        )

        processed = 0
        for settlement in settlements:
            try:
                SettlementService.process_settlement(settlement)
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
def send_payment_reminder(appointment_id):
    """
    یادآوری پرداخت بیعانه
    """
    from apps.bookings.models import Appointment
    from apps.notifications.services import NotificationService

    try:
        appointment = Appointment.objects.get(id=appointment_id)

        if not appointment.deposit_paid and appointment.deposit_amount > 0:
            NotificationService.send(
                user=appointment.customer,
                type='payment_reminder',
                title='یادآوری پرداخت بیعانه',
                body=f'لطفاً بیعانه {appointment.deposit_amount:,} تومان برای نوبت {appointment.service.name} را پرداخت کنید',
                data={'appointment_id': appointment.id},
            )

    except Exception as e:
        logger.error(f"Payment reminder failed for appointment {appointment_id}: {e}")


@shared_task
def check_expired_pending_transactions():
    """
    بررسی تراکنش‌های PENDING که بیش از ۳۰ دقیقه گذشته
    """
    from apps.payments.models import Transaction

    threshold = timezone.now() - timezone.timedelta(minutes=30)

    expired = Transaction.objects.filter(
        status=Transaction.Status.PENDING,
        created_at__lt=threshold,
    )

    count = expired.update(
        status=Transaction.Status.FAILED,
        failure_reason='انقضای زمان پرداخت',
    )

    logger.info(f"Expired {count} pending transactions")
    return {'expired': count}