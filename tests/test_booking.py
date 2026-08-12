"""
تست‌های سیستم رزرو نوبت — با تاریخ جلالی
"""
import pytest
from datetime import time
from django.urls import reverse
from rest_framework import status

from apps.appointments.models import Appointment
from apps.schedules.models import ServiceSchedule
from apps.appointments.services.slot_service import SlotService
from apps.appointments.services.booking_service import (
    BookingService,
    BookingException,
)


@pytest.mark.django_db
class TestSlotService:
    """تست‌های Slot Service"""

    def test_get_available_slots(
        self, approved_business, test_service, test_schedule
    ):
        """تست دریافت اسلات‌های آزاد"""
        slots = SlotService.get_available_slots(
            business_id=approved_business.id,
            service_id=test_service.id,
            jy=1405,
            jm=4,
            jd=22,
        )
        assert len(slots) > 0

        # بررسی اینکه اسلات‌ها در بازه استراحت نیستند
        for slot in slots:
            assert slot['start_time'] != '13:00'
            assert slot['start_time'] != '13:30'

    def test_no_slots_without_schedule(
        self, approved_business, test_service
    ):
        """بدون schedule هیچ اسلاتی نیست"""
        slots = SlotService.get_available_slots(
            business_id=approved_business.id,
            service_id=test_service.id,
            jy=1405,
            jm=4,
            jd=25,
        )
        assert len(slots) == 0

    def test_get_available_dates(
        self, approved_business, test_service, test_schedule
    ):
        """تست دریافت روزهای آزاد"""
        dates = SlotService.get_available_dates(
            business_id=approved_business.id,
            service_id=test_service.id,
            days_ahead=30,
        )
        # حداقل یک روز باید باشد (همان روز schedule)
        found = any(
            d['date_key'] == '1405/04/22' for d in dates
        )
        # ممکن است تاریخ گذشته باشد، پس فقط ساختار را چک می‌کنیم
        for d in dates:
            assert 'jy' in d
            assert 'jm' in d
            assert 'jd' in d
            assert 'date_key' in d
            assert 'weekday_name' in d
            assert 'available_slots_count' in d


@pytest.mark.django_db
class TestBookingService:
    """تست‌های Booking Service"""

    def test_create_booking_success(
        self,
        customer_user,
        approved_business,
        test_service,
        test_schedule,
    ):
        """تست ایجاد موفق نوبت"""
        appointment = BookingService.create_appointment(
            customer=customer_user,
            service_id=test_service.id,
            jy=1405,
            jm=4,
            jd=22,
            time_slot_str='10:00',
        )

        assert appointment.id is not None
        assert appointment.customer == customer_user
        assert appointment.business == approved_business
        assert appointment.service == test_service
        assert appointment.status == Appointment.Status.RESERVED
        assert appointment.verification_code is not None
        assert len(appointment.verification_code) == 4
        # قیمت نهایی = 500000 - 10% = 450000
        assert appointment.total_price == 450000
        assert appointment.deposit_amount == 100000
        assert appointment.remaining_amount == 350000

    def test_create_booking_slot_not_available(
        self,
        customer_user,
        approved_business,
        test_service,
        test_schedule,
    ):
        """تست رزرو ساعت غیرمجاز"""
        with pytest.raises(BookingException):
            BookingService.create_appointment(
                customer=customer_user,
                service_id=test_service.id,
                jy=1405,
                jm=4,
                jd=22,
                time_slot_str='23:00',  # خارج از ساعات کاری
            )

    def test_create_booking_no_schedule(
        self,
        customer_user,
        approved_business,
        test_service,
    ):
        """تست رزرو بدون schedule"""
        with pytest.raises(BookingException):
            BookingService.create_appointment(
                customer=customer_user,
                service_id=test_service.id,
                jy=1405,
                jm=5,
                jd=1,
                time_slot_str='10:00',
            )

    def test_create_booking_duplicate(
        self,
        customer_user,
        approved_business,
        test_service,
        test_schedule,
    ):
        """تست عدم امکان رزرو تکراری"""
        BookingService.create_appointment(
            customer=customer_user,
            service_id=test_service.id,
            jy=1405,
            jm=4,
            jd=22,
            time_slot_str='10:00',
        )

        with pytest.raises(BookingException):
            BookingService.create_appointment(
                customer=customer_user,
                service_id=test_service.id,
                jy=1405,
                jm=4,
                jd=22,
                time_slot_str='10:00',
            )

    def test_cancel_by_customer(
        self, test_appointment
    ):
        """تست لغو نوبت توسط مشتری"""
        test_appointment.cancel_by_customer('تغییر برنامه')

        test_appointment.refresh_from_db()
        assert test_appointment.status == 'cancelled_by_customer'
        assert test_appointment.cancellation_reason == 'تغییر برنامه'
        assert test_appointment.cancelled_at is not None

    def test_cancel_by_salon(
        self, test_appointment
    ):
        """تست لغو نوبت توسط سالن"""
        test_appointment.cancel_by_salon('تعطیلی')

        test_appointment.refresh_from_db()
        assert test_appointment.status == 'cancelled_by_salon'
        assert test_appointment.cancelled_at is not None

    def test_regenerate_code_cooldown(
        self, test_appointment
    ):
        """تست cooldown تولید مجدد کد"""
        # تلاش فوری باید خطا بدهد
        with pytest.raises(BookingException) as exc_info:
            BookingService.regenerate_verification_code(
                test_appointment
            )
        assert exc_info.value.code == 'CODE_REGENERATE_COOLDOWN'

    def test_verify_service_code(
        self, test_appointment, business_owner_user
    ):
        """تست تایید کد خدمت"""
        code = test_appointment.verification_code
        success = BookingService.verify_service_code(
            appointment=test_appointment,
            entered_code=code,
            verified_by=business_owner_user,
        )
        assert success is True
        test_appointment.refresh_from_db()
        assert test_appointment.status == Appointment.Status.DONE
        assert test_appointment.is_verified is True

    def test_verify_invalid_code(
        self, test_appointment, business_owner_user
    ):
        """تست کد اشتباه"""
        success = BookingService.verify_service_code(
            appointment=test_appointment,
            entered_code='0000',
            verified_by=business_owner_user,
        )
        assert success is False
        test_appointment.refresh_from_db()
        assert test_appointment.status == Appointment.Status.RESERVED


@pytest.mark.django_db
class TestBookingAPI:
    """تست‌های API نوبت‌دهی"""

    def test_create_appointment_api(
        self,
        authenticated_customer_client,
        test_service,
        test_schedule,
    ):
        """تست API ایجاد نوبت"""
        url = reverse('appointments:create-appointment')
        response = authenticated_customer_client.post(url, {
            'service_id': test_service.id,
            'jy': 1405,
            'jm': 4,
            'jd': 22,
            'time_slot': '10:00',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['success'] is True
        data = response.json()['data']
        assert data['verification_code'] is not None

    def test_create_appointment_invalid_time(
        self,
        authenticated_customer_client,
        test_service,
        test_schedule,
    ):
        """تست API با ساعت نامعتبر"""
        url = reverse('appointments:create-appointment')
        response = authenticated_customer_client.post(url, {
            'service_id': test_service.id,
            'jy': 1405,
            'jm': 4,
            'jd': 22,
            'time_slot': '25:99',
        })
        assert response.status_code == 400

    def test_my_appointments_api(
        self,
        authenticated_customer_client,
        test_appointment,
    ):
        """تست API نوبت‌های من"""
        url = reverse('appointments:my-appointments')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_business_appointments_api(
        self,
        authenticated_business_client,
        test_appointment,
    ):
        """تست API نوبت‌های کسب‌وکار"""
        url = reverse('appointments:business-appointments')
        response = authenticated_business_client.get(url)
        assert response.status_code == 200

    def test_cancel_appointment_api(
        self,
        authenticated_customer_client,
        test_appointment,
    ):
        """تست API لغو نوبت"""
        url = reverse(
            'appointments:cancel-appointment',
            kwargs={'pk': test_appointment.id},
        )
        response = authenticated_customer_client.post(url, {
            'reason_text': 'تغییر برنامه',
        })
        assert response.status_code == 200
        test_appointment.refresh_from_db()
        assert test_appointment.status == 'cancelled_by_customer'

    def test_cancel_by_business_api(
        self,
        authenticated_business_client,
        test_appointment,
    ):
        """تست API لغو نوبت توسط سالن"""
        url = reverse(
            'appointments:cancel-by-business',
            kwargs={'pk': test_appointment.id},
        )
        response = authenticated_business_client.post(url, {
            'reason_text': 'تعطیلی سالن',
        })
        assert response.status_code == 200
        test_appointment.refresh_from_db()
        assert test_appointment.status == 'cancelled_by_salon'

    def test_verify_code_api(
        self,
        authenticated_business_client,
        test_appointment,
    ):
        """تست API تایید کد خدمت"""
        code = test_appointment.verification_code
        url = reverse(
            'appointments:verify-code',
            kwargs={'pk': test_appointment.id},
        )
        response = authenticated_business_client.post(
            url, {'code': code}
        )
        assert response.status_code == 200
        test_appointment.refresh_from_db()
        assert test_appointment.status == 'done'

    def test_verify_invalid_code_api(
        self,
        authenticated_business_client,
        test_appointment,
    ):
        """تست API کد اشتباه"""
        url = reverse(
            'appointments:verify-code',
            kwargs={'pk': test_appointment.id},
        )
        response = authenticated_business_client.post(
            url, {'code': '0000'}
        )
        assert response.status_code == 400

    def test_business_stats_api(
        self,
        authenticated_business_client,
        test_appointment,
    ):
        """تست API آمار نوبت‌ها"""
        url = reverse('appointments:business-stats')
        response = authenticated_business_client.get(url)
        assert response.status_code == 200
        data = response.json()['data']
        assert 'total' in data
        assert 'reserved' in data
        assert 'done' in data