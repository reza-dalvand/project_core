"""
Booking Service - منطق اصلی ایجاد و مدیریت نوبت
"""
import random
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, Dict, Tuple

from django.db import transaction
from django.utils import timezone
from django.conf import settings

from apps.bookings.models import Appointment, TimeSlot, CancellationRequest
from apps.businesses.models import Service, Business, Employee
from apps.payments.models import Transaction, Wallet
from apps.accounts.models import CustomUser
from apps.core.exceptions import ZibanoBaseException


class BookingException(ZibanoBaseException):
    default_message = 'خطا در رزرو نوبت'
    default_code = 'BOOKING_ERROR'


class SlotNotAvailableException(BookingException):
    default_message = 'این ساعت دیگر آزاد نیست'
    default_code = 'SLOT_NOT_AVAILABLE'


class BusinessNotApprovedException(BookingException):
    default_message = 'این کسب‌وکار هنوز تایید نشده است'
    default_code = 'BUSINESS_NOT_APPROVED'


class ServiceNotActiveException(BookingException):
    default_message = 'این خدمت فعال نیست'
    default_code = 'SERVICE_NOT_ACTIVE'


class EmployeeNotFoundException(BookingException):
    default_message = 'کارمند مورد نظر یافت نشد'
    default_code = 'EMPLOYEE_NOT_FOUND'


class BookingService:
    """سرویس مدیریت نوبت‌ها"""

    # ─── کارمزد ───
    COMMISSION_PERCENT = Decimal('0.01')  # 1%
    MIN_COMMISSION = 10000  # حداقل ۱۰ هزار تومان

    @classmethod
    def calculate_commission(cls, amount: int) -> int:
        """محاسبه کارمزد: ۱٪ یا حداقل ۱۰ هزار تومان"""
        commission = int(amount * cls.COMMISSION_PERCENT)
        return max(commission, cls.MIN_COMMISSION)

    @classmethod
    @transaction.atomic
    def create_booking(
            cls,
            customer: CustomUser,
            service_id: int,
            target_date: date,
            start_time_str: str,
            employee_id: Optional[int] = None,
    ) -> Appointment:
        """
        ایجاد نوبت جدید

        Args:
            customer: کاربر مشتری
            service_id: شناسه خدمت
            target_date: تاریخ نوبت
            start_time_str: ساعت شروع (HH:MM)
            employee_id: شناسه کارمند (اختیاری)

        Returns:
            Appointment: نوبت ایجاد شده
        """
        # ─── ۱. اعتبارسنجی خدمت ───
        try:
            service = Service.objects.select_related('business').get(
                id=service_id,
                is_active=True,
            )
        except Service.DoesNotExist:
            raise ServiceNotActiveException()

        business = service.business

        if business.status != Business.Status.APPROVED:
            raise BusinessNotApprovedException()

        # ─── ۲. اعتبارسنجی کارمند ───
        employee = None
        if employee_id:
            try:
                employee = Employee.objects.get(
                    id=employee_id,
                    business=business,
                    is_active=True,
                    services=service,
                )
            except Employee.DoesNotExist:
                raise EmployeeNotFoundException()

        # ─── ۳. اعتبارسنجی ساعت ───
        try:
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except ValueError:
            raise BookingException(message='فرمت ساعت نامعتبر است')

        end_time = (
                datetime.combine(date.today(), start_time) +
                timedelta(minutes=service.duration_minutes)
        ).time()

        # ─── ۴. بررسی آزاد بودن اسلات ───
        from apps.bookings.services.slot_service import SlotService
        available_slots = SlotService.get_available_slots(
            business_id=business.id,
            service_id=service.id,
            target_date=target_date,
            employee_id=employee_id,
        )

        slot_available = any(
            s['start_time'] == start_time_str
            for s in available_slots
        )

        if not slot_available:
            raise SlotNotAvailableException()

        # ─── ۵. بررسی عدم تکراری بودن نوبت کاربر ───
        existing_booking = Appointment.objects.filter(
            customer=customer,
            date=target_date,
            time=start_time,
            status__in=[
                Appointment.Status.RESERVED,
                Appointment.Status.CONFIRMED,
            ]
        ).exists()

        if existing_booking:
            raise BookingException(
                message='شما در این تاریخ و ساعت نوبت دیگری دارید'
            )

        # ─── ۶. محاسبه قیمت‌ها ───
        original_price = service.original_price
        discount_percent = service.discount_percent or 0
        discount_amount = int(original_price * discount_percent / 100)
        final_price = max(0, original_price - discount_amount)

        deposit_amount = 0
        if service.has_deposit and service.deposit_amount > 0:
            deposit_amount = min(service.deposit_amount, final_price)

        # ─── ۷. تولید کد تایید ۴ رقمی ───
        verification_code = cls._generate_verification_code()

        # ─── ۸. ایجاد نوبت ───
        appointment = Appointment.objects.create(
            customer=customer,
            business=business,
            service=service,
            employee=employee,
            date=target_date,
            time=start_time,
            status=Appointment.Status.RESERVED,
            original_price=original_price,
            discount_percent=discount_percent,
            final_price=final_price,
            deposit_amount=deposit_amount,
            deposit_paid=False,
            verification_code=verification_code,
            code_generated_at=timezone.now(),
        )

        # ─── ۹. بروزرسانی آمار کسب‌وکار ───
        business.bookings_count = business.appointments.filter(
            status__in=[
                Appointment.Status.RESERVED,
                Appointment.Status.CONFIRMED,
                Appointment.Status.DONE,
            ]
        ).count()
        business.save(update_fields=['bookings_count'])

        return appointment

    @classmethod
    @transaction.atomic
    def confirm_deposit_payment(
            cls,
            appointment: Appointment,
            transaction_record: Transaction,
    ) -> Appointment:
        """
        تایید پرداخت بیعانه و فعال‌سازی نوبت
        """
        appointment.deposit_paid = True
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save(update_fields=['deposit_paid', 'status', 'updated_at'])

        # ─── ایجاد تراکنش بیعانه ───
        commission = cls.calculate_commission(transaction_record.amount)

        transaction_record.appointment = appointment
        transaction_record.business = appointment.business
        transaction_record.type = Transaction.Type.DEPOSIT
        transaction_record.status = Transaction.Status.SUCCESS
        transaction_record.original_price = appointment.original_price
        transaction_record.discount_amount = appointment.final_price - appointment.original_price
        transaction_record.commission_amount = commission
        transaction_record.net_amount = transaction_record.amount - commission
        transaction_record.paid_at = timezone.now()
        transaction_record.save()

        # ─── ارسال نوتیفیکیشن ───
        from apps.notifications.services import NotificationService
        NotificationService.send_booking_confirmed(appointment)

        return appointment

    @classmethod
    def _generate_verification_code(cls) -> str:
        """تولید کد تایید ۴ رقمی"""
        return str(random.randint(1000, 9999))

    @classmethod
    def regenerate_verification_code(cls, appointment: Appointment) -> str:
        """
        تولید مجدد کد تایید (هر ۵ دقیقه مجاز است)
        """
        if appointment.code_generated_at:
            elapsed = timezone.now() - appointment.code_generated_at
            if elapsed.total_seconds() < 300:  # ۵ دقیقه
                remaining = int(300 - elapsed.total_seconds())
                raise BookingException(
                    message=f'لطفاً {remaining} ثانیه صبر کنید',
                    code='CODE_REGENERATE_COOLDOWN',
                )

        new_code = cls._generate_verification_code()
        appointment.verification_code = new_code
        appointment.code_generated_at = timezone.now()
        appointment.save(update_fields=['verification_code', 'code_generated_at', 'updated_at'])

        return new_code

    @classmethod
    def verify_service_code(
            cls,
            appointment: Appointment,
            entered_code: str,
            verified_by: CustomUser,
    ) -> bool:
        """
        تایید کد خدمت توسط سالن‌دار
        """
        if appointment.verification_code != entered_code:
            return False

        if appointment.status != Appointment.Status.CONFIRMED:
            raise BookingException(
                message='این نوبت قابل تایید نیست',
                code='INVALID_APPOINTMENT_STATUS',
            )

        appointment.status = Appointment.Status.DONE
        appointment.verified_at = timezone.now()
        appointment.save(update_fields=['status', 'verified_at', 'updated_at'])

        # ─── ایجاد تراکنش تسویه ───
        if appointment.deposit_paid and appointment.deposit_amount > 0:
            commission = cls.calculate_commission(appointment.deposit_amount)
            net_amount = appointment.deposit_amount - commission

            Transaction.objects.create(
                user=appointment.customer,
                appointment=appointment,
                business=appointment.business,
                type=Transaction.Type.SETTLEMENT,
                status=Transaction.Status.SUCCESS,
                amount=appointment.deposit_amount,
                commission_amount=commission,
                net_amount=net_amount,
                settled_at=timezone.now(),
            )

        # ─── ارسال نوتیفیکیشن ───
        from apps.notifications.services import NotificationService
        NotificationService.send_booking_done(appointment)

        return True

    @classmethod
    @transaction.atomic
    def cancel_by_customer(
            cls,
            appointment: Appointment,
            reason_text: str = '',
    ) -> CancellationRequest:
        """
        لغو نوبت توسط مشتری
        """
        if appointment.status not in [
            Appointment.Status.RESERVED,
            Appointment.Status.CONFIRMED,
        ]:
            raise BookingException(
                message='این نوبت قابل لغو نیست',
                code='CANNOT_CANCEL',
            )

        # بررسی قوانین لغو
        now = timezone.now()
        appointment_datetime = datetime.combine(appointment.date, appointment.time)
        appointment_datetime = timezone.make_aware(appointment_datetime)

        hours_until = (appointment_datetime - now).total_seconds() / 3600

        # محاسبه جریمه
        penalty_amount = 0
        refund_amount = appointment.deposit_amount

        if hours_until > 2:
            # لغو تا ۲ ساعت قبل: جریمه ۳۰٪
            penalty_amount = int(appointment.deposit_amount * 0.3)
            refund_amount = appointment.deposit_amount - penalty_amount
        else:
            # لغو کمتر از ۲ ساعت: کل بیعانه جریمه
            penalty_amount = appointment.deposit_amount
            refund_amount = 0

        # ایجاد درخواست لغو
        cancellation = CancellationRequest.objects.create(
            appointment=appointment,
            requested_by=appointment.customer,
            reason_type=CancellationRequest.Reason.CUSTOMER_REQUEST,
            reason_text=reason_text,
            status=CancellationRequest.Status.APPROVED,  # لغو خودکار
            refund_amount=refund_amount,
            penalty_amount=penalty_amount,
            reviewed_at=timezone.now(),
        )

        # تغییر وضعیت نوبت
        appointment.status = Appointment.Status.CANCELLED_BY_CUSTOMER
        appointment.cancellation_reason = reason_text
        appointment.cancelled_at = timezone.now()
        appointment.save(update_fields=[
            'status', 'cancellation_reason', 'cancelled_at', 'updated_at'
        ])

        # استرداد وجه
        if refund_amount > 0 and appointment.deposit_paid:
            Transaction.objects.create(
                user=appointment.customer,
                appointment=appointment,
                business=appointment.business,
                type=Transaction.Type.REFUND,
                status=Transaction.Status.SUCCESS,
                amount=refund_amount,
                refunded_at=timezone.now(),
                description=f'استرداد بیعانه - لغو نوبت (جریمه: {penalty_amount:,} تومان)',
            )

        return cancellation

    @classmethod
    @transaction.atomic
    def cancel_by_business(
            cls,
            appointment: Appointment,
            reason_text: str,
            cancelled_by: CustomUser,
    ) -> CancellationRequest:
        """
        لغو نوبت توسط کسب‌وکار
        """
        if appointment.status not in [
            Appointment.Status.RESERVED,
            Appointment.Status.CONFIRMED,
        ]:
            raise BookingException(
                message='این نوبت قابل لغو نیست',
                code='CANNOT_CANCEL',
            )

        # لغو توسط سالن: استرداد کامل + ۱۰٪ غرامت
        refund_amount = appointment.deposit_amount
        penalty_amount = int(appointment.deposit_amount * 0.1)  # ۱۰٪ غرامت
        total_refund = refund_amount + penalty_amount

        cancellation = CancellationRequest.objects.create(
            appointment=appointment,
            requested_by=cancelled_by,
            reason_type=CancellationRequest.Reason.SALON_CLOSED,
            reason_text=reason_text,
            status=CancellationRequest.Status.APPROVED,
            refund_amount=total_refund,
            penalty_amount=0,
            reviewed_at=timezone.now(),
        )

        appointment.status = Appointment.Status.CANCELLED_BY_SALON
        appointment.cancellation_reason = reason_text
        appointment.cancelled_at = timezone.now()
        appointment.save(update_fields=[
            'status', 'cancellation_reason', 'cancelled_at', 'updated_at'
        ])

        # استرداد کامل + غرامت
        if appointment.deposit_paid and total_refund > 0:
            Transaction.objects.create(
                user=appointment.customer,
                appointment=appointment,
                business=appointment.business,
                type=Transaction.Type.REFUND,
                status=Transaction.Status.SUCCESS,
                amount=total_refund,
                refunded_at=timezone.now(),
                description=f'استرداد + غرامت لغو توسط سالن',
            )

        return cancellation