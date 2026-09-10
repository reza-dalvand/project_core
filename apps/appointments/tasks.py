"""
وظایف سلری برای مدیریت خودکار نوبت‌ها
✅ منطق انقضای ۳ روزه:
- نوبت‌های عادی: اگر تا ۳ روز بعد از نوبت کد تایید وارد نشود
  → لغو خودکار + استرداد بیعانه به مشتری
- نوبت‌های اعتمادی: بعد از ۳ روز
  → تایید خودکار + تسویه بیعانه به کسب‌وکار
"""
import logging
from datetime import datetime, timedelta

import jdatetime
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# تعداد روزهای مهلت برای ورود کد تایید
EXPIRY_DAYS = 3


@shared_task(bind=True, max_retries=3, name='apps.appointments.tasks.process_expired_appointments')
def process_expired_appointments(self):
    """
    بررسی خودکار نوبت‌های منقضی‌شده

    قوانین:
    ۱. نوبت‌های عادی (با کد):
       اگر تا ۳ روز بعد از زمان نوبت، کد تایید وارد نشود
       → لغو خودکار + استرداد بیعانه به مشتری

    ۲. نوبت‌های اعتمادی (بدون کد):
       بعد از ۳ روز → تایید خودکار
       → بیعانه به حساب کسب‌وکار واریز می‌شود
       → مسئولیت پلتفرم سلب می‌شود
    """
    from apps.appointments.models import Appointment

    reserved_appointments = Appointment.objects.filter(
        status=Appointment.Status.RESERVED,
    ).select_related('customer', 'business', 'service')

    processed_count = 0
    cancelled_count = 0
    confirmed_count = 0
    error_count = 0

    for appointment in reserved_appointments:
        try:
            # ─── محاسبه زمان انقضا ───
            gregorian_date = jdatetime.date(
                appointment.jy, appointment.jm, appointment.jd
            ).togregorian()

            apt_datetime = datetime.combine(gregorian_date, appointment.time_slot)
            apt_datetime = timezone.make_aware(apt_datetime)

            expiry_time = apt_datetime + timedelta(days=EXPIRY_DAYS)

            # اگر هنوز منقضی نشده، رد شو
            if timezone.now() < expiry_time:
                continue

            # ═══ نوبت منقضی شده ═══

            if appointment.is_trust_based:
                # ─── نوبت اعتمادی: تایید خودکار ───
                # بیعانه به حساب کسب‌وکار واریز می‌شود
                # تسویه توسط تسک auto_settle_completed_appointments انجام می‌شود
                appointment.status = Appointment.Status.DONE
                appointment.is_verified = True
                appointment.verified_at = timezone.now()
                appointment.done_at = timezone.now()
                appointment.save(update_fields=[
                    'status', 'is_verified', 'verified_at', 'done_at', 'updated_at',
                ])

                _notify_business_auto_confirm(appointment)

                confirmed_count += 1
                logger.info(
                    f"[EXPIRY] Trust-based appointment #{appointment.id} "
                    f"auto-confirmed (business: {appointment.business.name})"
                )

            else:
                # ─── نوبت عادی: لغو خودکار + استرداد ───
                refund_amount = appointment.deposit_amount

                reason = (
                    f'لغو خودکار: کد تایید ظرف {EXPIRY_DAYS} روز '
                    f'پس از نوبت وارد نشد'
                )

                appointment.status = Appointment.Status.CANCELLED_BY_CUSTOMER
                appointment.cancellation_reason = reason
                appointment.cancelled_at = timezone.now()
                appointment.save(update_fields=[
                    'status', 'cancellation_reason', 'cancelled_at', 'updated_at',
                ])

                # استرداد وجه به مشتری
                if refund_amount > 0:
                    try:
                        from apps.payments.services.payment_service import PaymentService
                        PaymentService.process_refund(
                            appointment=appointment,
                            refund_amount=refund_amount,
                            reason='لغو خودکار — عدم ورود کد تایید',
                        )
                    except Exception as e:
                        logger.error(
                            f"[EXPIRY] Refund failed for appointment "
                            f"#{appointment.id}: {e}"
                        )

                _notify_customer_auto_cancel(appointment, reason)

                cancelled_count += 1
                logger.info(
                    f"[EXPIRY] Appointment #{appointment.id} auto-cancelled "
                    f"(no verification code entered)"
                )

            processed_count += 1

        except Exception as e:
            error_count += 1
            logger.error(
                f"[EXPIRY] Error processing appointment "
                f"#{appointment.id}: {e}",
                exc_info=True,
            )
            continue

    logger.info(
        f"[EXPIRY] Batch complete — processed: {processed_count}, "
        f"cancelled: {cancelled_count}, confirmed: {confirmed_count}, "
        f"errors: {error_count}"
    )

    return {
        'processed': processed_count,
        'cancelled': cancelled_count,
        'confirmed': confirmed_count,
        'errors': error_count,
    }


def _notify_customer_auto_cancel(appointment, reason=''):
    """ارسال اعلان لغو خودکار به مشتری"""
    try:
        # ✅ Import صحیح از apps.notifications.services
        from apps.notifications.services import NotificationService
        NotificationService.send_booking_cancelled(
            appointment=appointment,
            reason=reason or 'عدم ورود کد تایید',
        )
    except Exception as e:
        logger.warning(
            f"[EXPIRY] Failed to notify customer for "
            f"appointment #{appointment.id}: {e}"
        )


def _notify_business_auto_confirm(appointment):
    """ارسال اعلان تایید خودکار به کسب‌وکار"""
    try:
        # ✅ Import صحیح از apps.notifications.services
        from apps.notifications.services import NotificationService
        NotificationService.send(
            user=appointment.business.owner,
            type='booking_done',
            title='نوبت به‌صورت خودکار تایید شد ✅',
            body=(
                f'نوبت «{appointment.service.name}» به‌صورت خودکار تایید شد. '
                f'مبلغ بیعانه به حساب شما واریز می‌شود.'
            ),
            data={'appointment_id': appointment.id},
            channels=['in_app'],
        )
    except Exception as e:
        logger.warning(
            f"[EXPIRY] Failed to notify business for "
            f"appointment #{appointment.id}: {e}"
        )


# در فایل apps/appointments/tasks.py اضافه شود:

@shared_task(name='apps.appointments.tasks.detect_excessive_cancellations')
def detect_excessive_cancellations():
    """
    تشخیص خودکار تخلف: ۵ لغو توسط سالن در ۲ روز گذشته
    این تسک فقط تخلف را ثبت می‌کند تا در لیست متخلفین داشبورد نمایش داده شود.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count
    from apps.appointments.models import Appointment
    from apps.businesses.models import BusinessViolation

    THRESHOLD = 5
    DAYS = 2
    cutoff = timezone.now() - timedelta(days=DAYS)

    # فقط لغوهای توسط سالن ملاک هستند
    violators = Appointment.objects.filter(
        status=Appointment.Status.CANCELLED_BY_SALON,
        cancelled_at__gte=cutoff
    ).values('business').annotate(
        cancel_count=Count('id')
    ).filter(cancel_count__gte=THRESHOLD)

    created_count = 0
    for v in violators:
        biz_id = v['business']
        count = v['cancel_count']
        
        # جلوگیری از ثبت تکراری برای یک بازه (اگر قبلاً فلگ شده و رسیدگی نشده)
        already_flagged = BusinessViolation.objects.filter(
            business_id=biz_id,
            is_resolved=False,
            created_at__gte=cutoff
        ).exists()
        
        if not already_flagged:
            BusinessViolation.objects.create(
                business_id=biz_id,
                cancellation_count=count,
                period_start=cutoff,
                period_end=timezone.now(),
            )
            created_count += 1

    logger.info(f"[VIOLATION] Detected {created_count} new business violations.")
    return {'new_violations_detected': created_count}