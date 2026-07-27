"""
Pytest fixtures مشترک
"""
import pytest
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
        role='customer',
        full_name='کاربر تست',
        is_verified=True,
    )


@pytest.fixture
def business_owner_user(db):
    """صاحب کسب‌وکار"""
    return User.objects.create_user(
        phone='09129876543',
        role='business_owner',
        full_name='صاحب کسب و کار',
        is_verified=True,
        national_id='0012345679',
        national_id_verified=True,
        verified_name='صاحب کسب و کار',
    )


@pytest.fixture
def admin_user(db):
    """ادمین"""
    return User.objects.create_superuser(
        phone='09120000000',
        password='admin123',
        role='super_admin',
        full_name='مدیر ارشد',
        is_verified=True,
    )


@pytest.fixture
def authenticated_customer_client(api_client, customer_user):
    """API Client با کاربر مشتری احراز هویت شده"""
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
            from apps.accounts.models import OTP
            from django.utils import timezone
            from datetime import timedelta

            return OTP.objects.create(
                phone=phone,
                user=user,
                code='12345',
                purpose=purpose or OTP.Purpose.LOGIN,
                expires_at=timezone.now() + timedelta(minutes=5),
            )

        @classmethod
        def verify_otp(cls, phone, code, purpose=None):
            from apps.accounts.models import OTP
            otp = OTP.objects.filter(phone=phone).first()
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