"""
Celery Tasks برای نوتیفیکیشن‌ها و وظایف پس‌زمینه
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════
#    یادآوری نوبت‌ها
# ══════════════════════════════════════════

@shared_task(bind=True, max_retries=3)
def send_booking_reminders(self):
    """
    ارسال یادآوری نوبت‌های فردا
    هر روز ساعت ۹ صبح اجرا می‌شود
    """
    from apps.bookings.models import Appointment
    from apps.notifications.services import NotificationService

    tomorrow = timezone.now().date() + timedelta(days=1)

    appointments = Appointment.objects.filter(
        date=tomorrow,
        status__in=[
            Appointment.Status.RESERVED,
            Appointment.Status.CONFIRMED,
        ],
    ).select_related('customer', 'business', 'service')

    sent_count = 0
    for appointment in appointments:
        try:
            NotificationService.send_booking_reminder(appointment)
            sent_count += 1
        except Exception as e:
            logger.error(
                f"Reminder failed for appointment {appointment.id}: {e}"
            )

    logger.info(f"Booking reminders sent: {sent_count}/{appointments.count()}")
    return {'sent': sent_count, 'total': appointments.count()}


@shared_task(bind=True, max_retries=3)
def send_same_day_reminders(self):
    """
    ارسال یادآوری نوبت‌های امروز (۲ ساعت قبل)
    هر ساعت اجرا می‌شود
    """
    from apps.bookings.models import Appointment
    from apps.notifications.services import NotificationService
    from datetime import datetime

    now = timezone.now()
    today = now.date()
    two_hours_later = (now + timedelta(hours=2)).time()

    # نوبت‌هایی که در ۲ ساعت آینده هستند
    appointments = Appointment.objects.filter(
        date=today,
        time__lte=two_hours_later,
        time__gte=now.time(),
        status__in=[
            Appointment.Status.RESERVED,
            Appointment.Status.CONFIRMED,
        ],
    ).select_related('customer', 'business', 'service')

    sent_count = 0
    for appointment in appointments:
        try:
            NotificationService.send(
                user=appointment.customer,
                type='booking_reminder',
                title='یادآوری نوبت امروز ⏰',
                body=(
                    f'تا ۲ ساعت دیگر نوبت {appointment.service.name} '
                    f'در {appointment.business.name} دارید.'
                ),
                data={'appointment_id': appointment.id},
                channels=['in_app', 'sms'],
                sms_template_type='booking_reminder',
                sms_variables={
                    'business_name': appointment.business.name,
                    'service_name': appointment.service.name,
                    'date': str(appointment.date),
                    'time': str(appointment.time),
                },
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Same-day reminder failed: {e}")

    logger.info(f"Same-day reminders sent: {sent_count}")
    return {'sent': sent_count}


# ══════════════════════════════════════════
#    تسویه خودکار
# ══════════════════════════════════════════

@shared_task(bind=True, max_retries=3)
def auto_settle_completed_appointments(self):
    """
    تسویه خودکار نوبت‌های انجام شده
    هر ۱ ساعت اجرا می‌شود
    """
    from apps.bookings.models import Appointment
    from apps.payments.models import Transaction
    from apps.payments.services.settlement_service import SettlementService

    # نوبت‌های انجام شده که بیعانه پرداخت شده
    appointments = Appointment.objects.filter(
        status=Appointment.Status.DONE,
        deposit_paid=True,
        verified_at__isnull=False,
    ).select_related('business', 'service')

    processed = 0
    errors = 0

    for appointment in appointments:
        # پیدا کردن تراکنش بیعانه
        tx = Transaction.objects.filter(
            appointment=appointment,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.SUCCESS,
            settled_at__isnull=True,
        ).first()

        if tx:
            try:
                SettlementService.release_deposit(appointment, tx)
                processed += 1
            except Exception as e:
                logger.error(
                    f"Auto-settle failed for appointment {appointment.id}: {e}"
                )
                errors += 1

    logger.info(
        f"Auto-settle completed: {processed} processed, {errors} errors"
    )
    return {'processed': processed, 'errors': errors}


@shared_task(bind=True, max_retries=3)
def process_pending_settlements(self):
    """
    پردازش تسویه‌های در انتظار (بیش از ۲۴ ساعت)
    هر ۶ ساعت اجرا می‌شود
    """
    from apps.payments.models import Settlement
    from apps.payments.services.settlement_service import SettlementService

    cutoff = timezone.now() - timedelta(hours=24)

    settlements = Settlement.objects.filter(
        status=Settlement.Status.PENDING,
        requested_at__lte=cutoff,
    ).select_related('business', 'bank_account')

    processed = 0
    for settlement in settlements:
        try:
            SettlementService.process_settlement(settlement)
            processed += 1
        except Exception as e:
            logger.error(
                f"Process settlement {settlement.id} failed: {e}"
            )

    logger.info(f"Pending settlements processed: {processed}")
    return {'processed': processed}


# ══════════════════════════════════════════
#    بررسی تراکنش‌ها
# ══════════════════════════════════════════

@shared_task
def check_expired_pending_transactions():
    """
    بررسی تراکنش‌های PENDING که بیش از ۳۰ دقیقه گذشته
    هر ۱۰ دقیقه اجرا می‌شود
    """
    from apps.payments.models import Transaction

    cutoff = timezone.now() - timedelta(minutes=30)

    expired = Transaction.objects.filter(
        status=Transaction.Status.PENDING,
        created_at__lt=cutoff,
    )

    count = expired.update(
        status=Transaction.Status.FAILED,
        failure_reason='انقضای زمان پرداخت (۳۰ دقیقه)',
    )

    if count > 0:
        logger.info(f"Expired {count} pending transactions")

    return {'expired': count}


@shared_task(bind=True, max_retries=3)
def verify_unconfirmed_payments(self):
    """
    بررسی و تایید پرداخت‌های تایید نشده از درگاه
    هر ۵ دقیقه اجرا می‌شود
    """
    from apps.payments.models import Transaction
    from apps.payments.services.zibal_service import ZibalService
    from apps.payments.services.settlement_service import SettlementService

    # تراکنش‌های PENDING که gateway_ref_id دارند
    transactions = Transaction.objects.filter(
        status=Transaction.Status.PENDING,
        gateway_ref_id__isnull=False,
        gateway=Transaction.Gateway.ZIBAL,
        created_at__gte=timezone.now() - timedelta(hours=2),
    ).select_related('appointment')

    verified = 0
    for tx in transactions:
        try:
            result = ZibalService.verify_payment(
                track_id=int(tx.gateway_ref_id),
                expected_amount_toman=tx.amount,
            )

            if result.get('success'):
                if tx.appointment:
                    SettlementService.process_deposit_payment(
                        tx.appointment, tx.amount, tx
                    )
                else:
                    tx.status = Transaction.Status.SUCCESS
                    tx.paid_at = timezone.now()
                    tx.gateway_ref_id = result.get('ref_number', tx.gateway_ref_id)
                    tx.save()

                verified += 1

        except Exception as e:
            logger.debug(
                f"Payment {tx.id} not yet confirmed: {e}"
            )

    if verified > 0:
        logger.info(f"Verified {verified} unconfirmed payments")

    return {'verified': verified}


# ══════════════════════════════════════════
#    پاکسازی
# ══════════════════════════════════════════

@shared_task
def cleanup_old_notifications():
    """
    حذف اعلان‌های قدیمی (بیش از ۹۰ روز)
    هر روز ساعت ۳ صبح اجرا می‌شود
    """
    from apps.notifications.services import NotificationService

    count = NotificationService.delete_old_notifications(days=90)
    logger.info(f"Cleaned up {count} old notifications")
    return {'deleted': count}


@shared_task
def cleanup_old_otp_codes():
    """
    حذف کدهای OTP قدیمی (بیش از ۲۴ ساعت)
    هر روز ساعت ۴ صبح اجرا می‌شود
    """
    from apps.accounts.models import OTP

    cutoff = timezone.now() - timedelta(hours=24)
    count, _ = OTP.objects.filter(
        created_at__lt=cutoff,
        is_used=True,
    ).delete()

    logger.info(f"Cleaned up {count} old OTP codes")
    return {'deleted': count}


@shared_task
def cleanup_expired_time_slots():
    """
    منقضی کردن اسلات‌های زمانی گذشته
    هر ساعت اجرا می‌شود
    """
    from apps.bookings.models import TimeSlot

    now = timezone.now()
    count = TimeSlot.objects.filter(
        date__lt=now.date(),
        status=TimeSlot.Status.AVAILABLE,
    ).update(status=TimeSlot.Status.EXPIRED)

    if count > 0:
        logger.info(f"Expired {count} old time slots")

    return {'expired': count}