"""
Pytest fixtures مشترک — نسخه جدید بدون role
هر کاربر می‌تواند یک کسب‌وکار داشته باشد
"""
import pytest
from datetime import time
import jdatetime
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client():
    """DRF API Client"""
    return APIClient()


@pytest.fixture
def customer_user(db):
    """کاربر عادی (مشتری)"""
    return User.objects.create_user(
        phone='09123456789',
        first_name='کاربر',
        last_name='تست',
        is_verified=True,
    )


@pytest.fixture
def business_owner_user(db):
    """صاحب کسب‌وکار"""
    return User.objects.create_user(
        phone='09129876543',
        first_name='صاحب',
        last_name='کسب و کار',
        is_verified=True,
        national_id='0012345679',
        is_national_id_verified=True,
        verified_name='صاحب کسب و کار',
    )


@pytest.fixture
def admin_user(db):
    """ادمین"""
    return User.objects.create_superuser(
        phone='09120000000',
        password='admin123',
        first_name='مدیر',
        last_name='ارشد',
        is_verified=True,
    )


@pytest.fixture
def authenticated_customer_client(api_client, customer_user):
    """API Client با کاربر مشتری"""
    refresh = RefreshToken.for_user(customer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = customer_user
    return api_client


@pytest.fixture
def authenticated_business_client(api_client, business_owner_user):
    """API Client با صاحب کسب‌وکار"""
    refresh = RefreshToken.for_user(business_owner_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = business_owner_user
    return api_client


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """API Client با ادمین"""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = admin_user
    return api_client


@pytest.fixture
def mock_otp(monkeypatch):
    """Mock کردن OTP Service"""
    class MockOTPService:
        @classmethod
        def send_otp(cls, phone, purpose=None, user=None):
            from apps.accounts.models import OtpCode
            from django.utils import timezone
            from datetime import timedelta
            return OtpCode.objects.create(
                phone=phone,
                code='12345',
                purpose=purpose or OtpCode.Purpose.LOGIN,
                expires_at=timezone.now() + timedelta(minutes=5),
            )

        @classmethod
        def verify_otp(cls, phone, code, purpose=None):
            from apps.accounts.models import OtpCode
            otp = OtpCode.objects.filter(phone=phone).first()
            if otp:
                otp.is_used = True
                otp.save()
            return otp

    from apps.accounts.services import otp_service
    monkeypatch.setattr(otp_service, 'OTPService', MockOTPService)
    return MockOTPService


@pytest.fixture
def mock_shahkar(monkeypatch):
    """Mock کردن Shahkar Service"""
    class MockShahkar:
        @classmethod
        def verify(cls, national_id, phone, full_name=None):
            return {
                'success': True,
                'verified_name': full_name or 'نام تایید شده',
                'national_id': national_id,
            }

    from apps.accounts.services import shahkar_service
    monkeypatch.setattr(shahkar_service, 'ShahkarService', MockShahkar)
    return MockShahkar


# ═══════════════════════════════════════════════
#   Fixtures برای ساختار جدید
# ═══════════════════════════════════════════════

@pytest.fixture
def service_category(db):
    """دسته‌بندی خدمات"""
    from apps.categories.models import ServiceCategory
    return ServiceCategory.objects.create(
        name='پوست و فیشیال',
        icon_name='spa',
        color='#4CAF50',
        gradient_start='#4CAF50',
        gradient_end='#388E3C',
        sort_order=1,
    )


@pytest.fixture
def sub_service(service_category):
    """زیرخدمت"""
    from apps.categories.models import SubService
    return SubService.objects.create(
        category=service_category,
        name='فیشیال VIP',
        type_id='facial_vip',
    )


@pytest.fixture
def business_category(db):
    """نوع کسب‌وکار"""
    from apps.categories.models import BusinessCategory
    return BusinessCategory.objects.create(name='سالن زیبایی')


@pytest.fixture
def province(db):
    """استان"""
    from apps.locations.models import Province
    return Province.objects.create(name='تهران')


@pytest.fixture
def city(province):
    """شهر"""
    from apps.locations.models import City
    return City.objects.create(name='تهران', province=province)


@pytest.fixture
def approved_business(business_owner_user, business_category, province, city):
    """کسب‌وکار تایید شده"""
    from apps.businesses.models import Business
    return Business.objects.create(
        owner=business_owner_user,
        name='سالن تست',
        category=business_category,
        province=province,
        city=city,
        address='آدرس تست',
        status='approved',
    )


@pytest.fixture
def test_service(approved_business, service_category, sub_service):
    """خدمت تست"""
    from apps.services.models import Service
    return Service.objects.create(
        business=approved_business,
        name='فیشیال تخصصی',
        category=service_category,
        sub_service=sub_service,
        original_price=500000,
        discount_percent=10,
        has_deposit=True,
        deposit_amount=100000,
        duration=60,
        renewal_days=30,
    )


@pytest.fixture
def test_schedule(approved_business, test_service):
    """زمان‌بندی تست"""
    from apps.schedules.models import ServiceSchedule
    return ServiceSchedule.objects.create(
        business=approved_business,
        service=test_service,
        jy=1405,
        jm=4,
        jd=22,
        work_start=time(9, 0),
        work_end=time(18, 0),
        slot_duration=30,
        breaks=[{'start': '13:00', 'end': '14:00'}],
    )


@pytest.fixture
def test_appointment(customer_user, approved_business, test_service):
    """نوبت تست"""
    from apps.appointments.models import Appointment
    return Appointment.objects.create(
        business=approved_business,
        service=test_service,
        customer=customer_user,
        jy=1405,
        jm=4,
        jd=22,
        time_slot=time(10, 0),
        status=Appointment.Status.RESERVED,
        total_price=450000,
        deposit_amount=100000,
    )