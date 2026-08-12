"""
Booking Service — منطق اصلی ایجاد و مدیریت نوبت
با تاریخ جلالی
"""
import logging
import random
from datetime import datetime, timedelta

import jdatetime
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.businesses.models import Business
from apps.services.models import Service
from apps.core.utils import jalali_to_key
# ✅ import از core به جای تعریف محلی
from apps.core.exceptions import (
    BookingException,
    SlotNotAvailableException,
)

logger = logging.getLogger(__name__)


# ✅ Exception‌های خاص booking که در core نیستند
class BusinessNotApprovedException(BookingException):
    default_message = 'این کسب‌وکار هنوز تایید نشده است'
    default_code = 'BUSINESS_NOT_APPROVED'


class ServiceNotActiveException(BookingException):
    default_message = 'این خدمت فعال نیست'
    default_code = 'SERVICE_NOT_ACTIVE'


class BookingService:
    """سرویس مدیریت نوبت‌ها — با تاریخ جلالی"""

    @classmethod
    def calculate_commission(cls, amount: int) -> int:
        """محاسبه کارمزد زیبانو: ۱٪ حداقل ۱۰,۰۰۰ تومان"""
        if amount <= 0:
            return 0
        commission = int(amount * 0.01)
        return max(commission, 10000)

    @classmethod
    @transaction.atomic
    def create_appointment(
        cls,
        customer,
        service_id: int,
        jy: int,
        jm: int,
        jd: int,
        time_slot_str: str,
    ) -> Appointment:
        try:
            service = Service.objects.select_related('business').only(
                'id', 'name', 'original_price', 'discount_percent',
                'has_deposit', 'deposit_amount', 'duration',
                'business__id', 'business__name', 'business__status',
                'business__booking_link_bookings',
            ).get(id=service_id, is_active=True)
        except Service.DoesNotExist:
            raise BookingException(
                message='خدمت مورد نظر یافت نشد',
                code='SERVICE_NOT_FOUND',
            )

        business = service.business
        if business.status != Business.Status.APPROVED:
            raise BusinessNotApprovedException()

        try:
            time_slot = datetime.strptime(time_slot_str, '%H:%M').time()
        except ValueError:
            raise BookingException(
                message='فرمت ساعت نامعتبر است (HH:MM)',
                code='INVALID_TIME_FORMAT',
            )

        from apps.appointments.services.slot_service import SlotService
        available_slots = SlotService.get_available_slots(
            business_id=business.id,
            service_id=service.id,
            jy=jy, jm=jm, jd=jd,
        )

        slot_available = any(
            s['start_time'] == time_slot_str
            for s in available_slots
        )
        if not slot_available:
            raise SlotNotAvailableException()

        has_existing = Appointment.objects.filter(
            customer=customer,
            jy=jy, jm=jm, jd=jd,
            time_slot=time_slot,
            status=Appointment.Status.RESERVED,
        ).exists()
        if has_existing:
            raise BookingException(
                message='شما در این تاریخ و ساعت نوبت دیگری دارید',
                code='DUPLICATE_APPOINTMENT',
            )

        original_price = service.original_price
        discount_percent = service.discount_percent or 0
        discount_amount = int(original_price * discount_percent / 100)
        final_price = max(0, original_price - discount_amount)

        deposit_amount = 0
        if service.has_deposit and service.deposit_amount > 0:
            deposit_amount = min(service.deposit_amount, final_price)
        remaining_amount = final_price - deposit_amount

        verification_code = cls._generate_verification_code()

        date_key = jalali_to_key(jy, jm, jd)

        appointment = Appointment.objects.create(
            business=business,
            service=service,
            customer=customer,
            jy=jy, jm=jm, jd=jd,
            date_key=date_key,
            time_slot=time_slot,
            status=Appointment.Status.RESERVED,
            verification_code=verification_code,
            total_price=final_price,
            deposit_amount=deposit_amount,
            remaining_amount=remaining_amount,
        )

        Business.objects.filter(id=business.id).update(
            booking_link_bookings=F('booking_link_bookings') + 1,
        )

        logger.info(
            f"Appointment created: customer={customer.phone}, "
            f"business={business.name}, date_key={date_key}, "
            f"time={time_slot_str}"
        )
        return appointment

    @classmethod
    def regenerate_verification_code(cls, appointment: Appointment) -> str:
        if appointment.updated_at:
            elapsed = timezone.now() - appointment.updated_at
            if elapsed.total_seconds() < 300:
                remaining = int(300 - elapsed.total_seconds())
                raise BookingException(
                    message=f'لطفاً {remaining} ثانیه صبر کنید',
                    code='CODE_REGENERATE_COOLDOWN',
                )
        new_code = cls._generate_verification_code()
        appointment.verification_code = new_code
        appointment.save(update_fields=['verification_code', 'updated_at'])
        return new_code

    @classmethod
    def verify_service_code(
        cls,
        appointment: Appointment,
        entered_code: str,
        verified_by,
    ) -> bool:
        if appointment.verification_code != entered_code:
            return False
        if appointment.status != Appointment.Status.RESERVED:
            raise BookingException(
                message='این نوبت قابل تایید نیست',
                code='INVALID_APPOINTMENT_STATUS',
            )
        appointment.status = Appointment.Status.DONE
        appointment.is_verified = True
        appointment.verified_at = timezone.now()
        appointment.save(update_fields=[
            'status', 'is_verified', 'verified_at', 'updated_at',
        ])
        return True

    @classmethod
    @transaction.atomic
    def cancel_by_customer(
        cls,
        appointment: Appointment,
        reason_text: str = '',
    ):
        if appointment.status != Appointment.Status.RESERVED:
            raise BookingException(
                message='این نوبت قابل لغو نیست',
                code='CANNOT_CANCEL',
            )

        penalty_amount = 0
        refund_amount = appointment.deposit_amount

        try:
            parts = appointment.date_key.split('/')
            jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
            gregorian_date = jdatetime.date(jy, jm, jd).togregorian()
            apt_datetime = datetime.combine(gregorian_date, appointment.time_slot)
            apt_datetime = timezone.make_aware(apt_datetime)
            hours_until = (apt_datetime - timezone.now()).total_seconds() / 3600

            if hours_until > 2:
                penalty_amount = int(appointment.deposit_amount * 0.3)
                refund_amount = appointment.deposit_amount - penalty_amount
            else:
                penalty_amount = appointment.deposit_amount
                refund_amount = 0
        except Exception:
            pass

        appointment.status = Appointment.Status.CANCELLED_BY_CUSTOMER
        appointment.cancellation_reason = reason_text
        appointment.cancelled_at = timezone.now()
        appointment.save(update_fields=[
            'status', 'cancellation_reason', 'cancelled_at', 'updated_at',
        ])

        if refund_amount > 0 and appointment.deposit_amount > 0:
            from apps.payments.services.payment_service import PaymentService
            PaymentService.process_refund(
                appointment=appointment,
                refund_amount=refund_amount,
                reason=f'لغو توسط مشتری (جریمه: {penalty_amount:,} تومان)',
            )

    @classmethod
    @transaction.atomic
    def cancel_by_business(
        cls,
        appointment: Appointment,
        reason_text: str,
        cancelled_by,
    ):
        if appointment.status != Appointment.Status.RESERVED:
            raise BookingException(
                message='این نوبت قابل لغو نیست',
                code='CANNOT_CANCEL',
            )

        refund_amount = appointment.deposit_amount

        appointment.status = Appointment.Status.CANCELLED_BY_SALON
        appointment.cancellation_reason = reason_text
        appointment.cancelled_at = timezone.now()
        appointment.save(update_fields=[
            'status', 'cancellation_reason', 'cancelled_at', 'updated_at',
        ])

        if refund_amount > 0:
            from apps.payments.services.payment_service import PaymentService
            PaymentService.process_refund(
                appointment=appointment,
                refund_amount=refund_amount,
                reason='لغو توسط سالن — استرداد کامل',
            )

    @staticmethod
    def _generate_verification_code() -> str:
        return ''.join([str(random.randint(0, 9)) for _ in range(4)])