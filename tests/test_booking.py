"""
تست‌های سیستم رزرو نوبت
"""
import pytest
from datetime import date, timedelta, time
from django.urls import reverse
from rest_framework import status

# ✅ اصلاح شده: Schedule و ScheduleBreak از bookings ایمپورت می‌شوند
from apps.bookings.models import Appointment, Schedule, ScheduleBreak
from apps.bookings.services.slot_service import SlotService
from apps.businesses.models import Service, Business
from apps.bookings.services.booking_service import BookingService, BookingException

@pytest.fixture
def approved_business_with_service(business_owner_user):
    """کسب‌وکار تایید شده با خدمت و برنامه کاری"""
    from apps.businesses.models import Province, City, Category

    province = Province.objects.create(name='تهران', slug='tehran')
    city = City.objects.create(name='تهران', slug='tehran', province=province)
    category = Category.objects.create(name='سالن زیبایی', slug='salon')

    business = Business.objects.create(
        owner=business_owner_user,
        name='سالن تست',
        category=category,
        province=province,
        city=city,
        address='آدرس تست',
        status=Business.Status.APPROVED,
    )

    service = Service.objects.create(
        business=business,
        name='فیشیال تخصصی',
        original_price=500000,
        discount_percent=10,
        has_deposit=True,
        deposit_amount=100000,
        duration_minutes=60,
        is_active=True,
    )

    # برنامه کاری: شنبه (0)
    schedule = Schedule.objects.create(
        business=business,
        service=service,
        weekday=0,  # شنبه
        is_working=True,
        start_time=time(9, 0),
        end_time=time(18, 0),
        slot_duration=30,
    )

    # استراحت ناهار
    ScheduleBreak.objects.create(
        schedule=schedule,
        start_time=time(13, 0),
        end_time=time(14, 0),
    )

    return {
        'business': business,
        'service': service,
        'schedule': schedule,
    }


@pytest.fixture
def next_saturday():
    """تاریخ شنبه آینده"""
    today = date.today()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7
    return today + timedelta(days=days_until_saturday)


@pytest.mark.django_db
class TestSlotService:
    """تست‌های Slot Service"""

    def test_get_available_slots(
            self, approved_business_with_service, next_saturday
    ):
        """تست دریافت اسلات‌های آزاد"""
        data = approved_business_with_service

        slots = SlotService.get_available_slots(
            business_id=data['business'].id,
            service_id=data['service'].id,
            target_date=next_saturday,
        )

        assert len(slots) > 0

        # بررسی اینکه اسلات‌ها در بازه استراحت نیستند
        for slot in slots:
            assert slot['start_time'] != '13:00'
            assert slot['start_time'] != '13:30'

    def test_get_available_dates(
            self, approved_business_with_service
    ):
        """تست دریافت روزهای آزاد"""
        data = approved_business_with_service

        dates = SlotService.get_available_dates(
            business_id=data['business'].id,
            service_id=data['service'].id,
            days_ahead=30,
        )

        assert len(dates) > 0

        for d in dates:
            assert 'jy' in d
            assert 'jm' in d
            assert 'jd' in d
            assert 'weekday_name' in d
            assert 'available_slots_count' in d
            assert d['available_slots_count'] > 0


@pytest.mark.django_db
class TestBookingService:
    """تست‌های Booking Service"""

    def test_create_booking_success(
            self, customer_user, approved_business_with_service, next_saturday
    ):
        """تست ایجاد موفق نوبت"""
        data = approved_business_with_service

        appointment = BookingService.create_booking(
            customer=customer_user,
            service_id=data['service'].id,
            target_date=next_saturday,
            start_time_str='10:00',
        )

        assert appointment.id is not None
        assert appointment.customer == customer_user
        assert appointment.business == data['business']
        assert appointment.service == data['service']
        assert appointment.status == Appointment.Status.RESERVED
        assert appointment.verification_code is not None
        assert len(appointment.verification_code) == 4
        assert appointment.final_price == 450000  # 500000 - 10%
        assert appointment.deposit_amount == 100000

    def test_create_booking_duplicate(
            self, customer_user, approved_business_with_service, next_saturday
    ):
        """تست عدم امکان رزرو تکراری"""
        data = approved_business_with_service

        # اولین رزرو
        BookingService.create_booking(
            customer=customer_user,
            service_id=data['service'].id,
            target_date=next_saturday,
            start_time_str='10:00',
        )

        # تلاش برای رزرو تکراری
        with pytest.raises(BookingException):
            BookingService.create_booking(
                customer=customer_user,
                service_id=data['service'].id,
                target_date=next_saturday,
                start_time_str='10:00',
            )

    def test_regenerate_code_cooldown(
            self, customer_user, approved_business_with_service, next_saturday
    ):
        """تست cooldown تولید مجدد کد"""
        data = approved_business_with_service

        appointment = BookingService.create_booking(
            customer=customer_user,
            service_id=data['service'].id,
            target_date=next_saturday,
            start_time_str='10:00',
        )

        # تلاش فوری برای regenerate باید خطا بدهد
        with pytest.raises(BookingException) as exc_info:
            BookingService.regenerate_verification_code(appointment)

        assert exc_info.value.code == 'CODE_REGENERATE_COOLDOWN'

    def test_cancel_by_customer(
            self, customer_user, approved_business_with_service, next_saturday
    ):
        """تست لغو نوبت توسط مشتری"""
        data = approved_business_with_service

        appointment = BookingService.create_booking(
            customer=customer_user,
            service_id=data['service'].id,
            target_date=next_saturday,
            start_time_str='10:00',
        )
        appointment.deposit_paid = True
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save()

        cancellation = BookingService.cancel_by_customer(
            appointment=appointment,
            reason_text='تغییر برنامه',
        )

        assert cancellation is not None
        assert appointment.status == Appointment.Status.CANCELLED_BY_CUSTOMER
        assert cancellation.refund_amount > 0


@pytest.mark.django_db
class TestBookingAPI:
    """تست‌های API نوبت‌دهی"""

    def test_available_dates_api(
            self, authenticated_customer_client, approved_business_with_service
    ):
        """تست API روزهای آزاد"""
        data = approved_business_with_service

        url = reverse('api:bookings:available-dates')
        response = authenticated_customer_client.get(url, {
            'service_id': data['service'].id,
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True
        assert len(response.json()['data']) > 0

    def test_available_slots_api(
            self, authenticated_customer_client, approved_business_with_service, next_saturday
    ):
        """تست API ساعات آزاد"""
        data = approved_business_with_service

        url = reverse('api:bookings:available-slots')
        response = authenticated_customer_client.get(url, {
            'service_id': data['service'].id,
            'date': next_saturday.isoformat(),
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True

    def test_create_booking_api(
            self, authenticated_customer_client, approved_business_with_service, next_saturday
    ):
        """تست API ایجاد نوبت"""
        data = approved_business_with_service

        url = reverse('api:bookings:create-booking')
        response = authenticated_customer_client.post(url, {
            'service_id': data['service'].id,
            'date': next_saturday.isoformat(),
            'time': '10:00',
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['success'] is True
        assert 'verification_code' in response.json()['data']

    def test_my_appointments_api(
            self, authenticated_customer_client, customer_user,
            approved_business_with_service, next_saturday
    ):
        """تست API نوبت‌های من"""
        data = approved_business_with_service

        # ایجاد نوبت
        BookingService.create_booking(
            customer=customer_user,
            service_id=data['service'].id,
            target_date=next_saturday,
            start_time_str='10:00',
        )

        url = reverse('api:bookings:my-appointments')
        response = authenticated_customer_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True
        assert len(response.json()['results']) > 0

    def test_business_appointments_api(
            self, authenticated_business_client, business_owner_user,
            customer_user, approved_business_with_service, next_saturday
    ):
        """تست API نوبت‌های کسب‌وکار"""
        data = approved_business_with_service

        # ایجاد نوبت
        BookingService.create_booking(
            customer=customer_user,
            service_id=data['service'].id,
            target_date=next_saturday,
            start_time_str='10:00',
        )

        url = reverse('api:bookings:business-appointments')
        response = authenticated_business_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True

    def test_verify_code_api(
            self, authenticated_business_client, business_owner_user,
            customer_user, approved_business_with_service, next_saturday
    ):
        """تست API تایید کد خدمت"""
        data = approved_business_with_service

        # ایجاد و تایید نوبت
        appointment = BookingService.create_booking(
            customer=customer_user,
            service_id=data['service'].id,
            target_date=next_saturday,
            start_time_str='10:00',
        )
        appointment.deposit_paid = True
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save()

        code = appointment.verification_code

        url = reverse('api:bookings:verify-code', kwargs={'pk': appointment.id})
        response = authenticated_business_client.post(url, {
            'code': code,
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True

        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.DONE

    def test_cancel_booking_api(
            self, authenticated_customer_client, customer_user,
            approved_business_with_service, next_saturday
    ):
        """تست API لغو نوبت"""
        data = approved_business_with_service

        appointment = BookingService.create_booking(
            customer=customer_user,
            service_id=data['service'].id,
            target_date=next_saturday,
            start_time_str='10:00',
        )

        url = reverse('api:bookings:cancel-booking', kwargs={'pk': appointment.id})
        response = authenticated_customer_client.post(url, {
            'reason_text': 'تغییر برنامه',
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True