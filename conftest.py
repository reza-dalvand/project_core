"""
Pytest fixtures مشترک — بدون role
هر کاربر می‌تواند یک کسب‌وکار داشته باشد
"""
import pytest
from datetime import time
import jdatetime
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ═══════════════════════════════════════════════
#   Clients
# ═══════════════════════════════════════════════
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
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
    )
    api_client.user = customer_user
    return api_client


@pytest.fixture
def authenticated_business_client(api_client, business_owner_user):
    """API Client با صاحب کسب‌وکار"""
    refresh = RefreshToken.for_user(business_owner_user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
    )
    api_client.user = business_owner_user
    return api_client


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """API Client با ادمین"""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
    )
    api_client.user = admin_user
    return api_client


# ═══════════════════════════════════════════════
#   Mock Services
# ═══════════════════════════════════════════════
@pytest.fixture
def mock_otp(monkeypatch):
    """Mock کردن OTP Service — نسخه کامل"""

    class MockOtpCode:
        """شبیه‌سازی آبجکت OtpCode"""
        def __init__(self, phone, code='12345'):
            self.phone = phone
            self.code = code
            self.is_used = False

    class MockOTPService:
        _sent_codes = {}

        @classmethod
        def send_otp(cls, phone, purpose=None, user=None):
            otp = MockOtpCode(phone)
            cls._sent_codes[phone] = otp.code
            return otp

        @classmethod
        def verify_otp(cls, phone, code, purpose=None):
            return MockOtpCode(phone, code)

    from apps.accounts.services import otp_service
    from apps.accounts.views import auth as auth_views
    from apps.accounts.views import profile as profile_views

    monkeypatch.setattr(otp_service, 'OTPService', MockOTPService)
    monkeypatch.setattr(auth_views, 'OTPService', MockOTPService)
    monkeypatch.setattr(profile_views, 'OTPService', MockOTPService)
    return MockOTPService


@pytest.fixture
def mock_shahkar(monkeypatch):
    """Mock کردن Shahkar Service — نسخه کامل"""

    class MockShahkar:
        @classmethod
        def verify(cls, national_id, phone, full_name=None):
            return {
                'success': True,
                'verified_name': full_name or 'نام تایید شده',
                'national_id': national_id,
            }

    from apps.accounts.services import shahkar_service
    from apps.accounts.views import auth as auth_views

    monkeypatch.setattr(shahkar_service, 'ShahkarService', MockShahkar)
    monkeypatch.setattr(auth_views, 'ShahkarService', MockShahkar)
    return MockShahkar


# ═══════════════════════════════════════════════
#   Lookup Data
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


# ═══════════════════════════════════════════════
#   Business & Service
# ═══════════════════════════════════════════════
@pytest.fixture
def approved_business(
    business_owner_user, business_category, province, city
):
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


# ═══════════════════════════════════════════════
#   Schedule & Appointment
# ═══════════════════════════════════════════════
@pytest.fixture
def test_schedule(approved_business, test_service):
    """زمان‌بندی تست - با تاریخ پویا (۳۰ روز آینده)"""
    from apps.schedules.models import ServiceSchedule
    future_date = jdatetime.date.today() + jdatetime.timedelta(days=30)
    return ServiceSchedule.objects.create(
        business=approved_business,
        service=test_service,
        jy=future_date.year,
        jm=future_date.month,
        jd=future_date.day,
        work_start=time(9, 0),
        work_end=time(18, 0),
        slot_duration=30,
        breaks=[{'start': '13:00', 'end': '14:00'}],
    )


@pytest.fixture
def test_appointment(customer_user, approved_business, test_service):
    """نوبت تست - با تاریخ پویا (۳۰ روز آینده)"""
    from apps.appointments.models import Appointment
    future_date = jdatetime.date.today() + jdatetime.timedelta(days=30)
    return Appointment.objects.create(
        business=approved_business,
        service=test_service,
        customer=customer_user,
        jy=future_date.year,
        jm=future_date.month,
        jd=future_date.day,
        time_slot=time(10, 0),
        status=Appointment.Status.RESERVED,
        total_price=450000,
        deposit_amount=100000,
    )





# ═══════════════════════════════════════════════
#   فیکسچرهای داشبورد ادمین — فاز ۶
# ═══════════════════════════════════════════════
from django.utils import timezone as django_timezone


@pytest.fixture
def dashboard_admin_role(db):
    """نقش سوپر ادمین داشبورد"""
    from apps.dashboard.models import AdminRole
    role, _ = AdminRole.objects.get_or_create(
        name=AdminRole.Role.SUPER_ADMIN,
        defaults={
            'description': 'دسترسی کامل به تمام بخش‌ها',
            'permissions': ['users', 'businesses', 'financial',
                            'content', 'support', 'settings'],
        },
    )
    return role


@pytest.fixture
def dashboard_app_admin_role(db):
    """نقش ادمین اپلیکیشن داشبورد"""
    from apps.dashboard.models import AdminRole
    role, _ = AdminRole.objects.get_or_create(
        name=AdminRole.Role.APP_ADMIN,
        defaults={
            'description': 'دسترسی به بخش کاربران و کسب‌وکارها',
            'permissions': ['users', 'businesses'],
        },
    )
    return role


@pytest.fixture
def dashboard_admin_user(db):
    """کاربر ادمین داشبورد"""
    return User.objects.create_user(
        phone='09121111111',
        first_name='ادمین',
        last_name='داشبورد',
        is_staff=True,
        is_verified=True,
    )


@pytest.fixture
def dashboard_admin_profile(dashboard_admin_user, dashboard_admin_role):
    """پروفایل ادمین داشبورد (AdminUser)"""
    from apps.dashboard.models import AdminUser
    admin, _ = AdminUser.objects.get_or_create(
        user=dashboard_admin_user,
        defaults={
            'role': dashboard_admin_role,
            'is_active': True,
        },
    )
    return admin


@pytest.fixture
def dashboard_client(client, dashboard_admin_user, dashboard_admin_profile):
    """
    کلاینت با سشن داشبورد فعال (نقش super_admin)
    شبیه‌سازی ورود موفق به داشبورد بدون نیاز به OTP
    """
    session = client.session
    session['dashboard_admin_logged_in'] = True
    session['dashboard_admin_phone'] = dashboard_admin_user.phone
    session['dashboard_role'] = 'super_admin'
    session['dashboard_login_time'] = django_timezone.now().isoformat()
    session.save()
    return client


@pytest.fixture
def dashboard_app_admin_client(client, dashboard_admin_user, dashboard_app_admin_role):
    """
    کلاینت با سشن داشبورد فعال (نقش app_admin)
    برای تست محدودیت‌های دسترسی
    """
    from apps.dashboard.models import AdminUser
    AdminUser.objects.get_or_create(
        user=dashboard_admin_user,
        defaults={
            'role': dashboard_app_admin_role,
            'is_active': True,
        },
    )
    session = client.session
    session['dashboard_admin_logged_in'] = True
    session['dashboard_admin_phone'] = dashboard_admin_user.phone
    session['dashboard_role'] = 'app_admin'
    session['dashboard_login_time'] = django_timezone.now().isoformat()
    session.save()
    return client