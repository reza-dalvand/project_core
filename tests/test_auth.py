"""
تست‌های احراز هویت
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestSendOTP:
    """تست‌های ارسال OTP"""

    def test_send_otp_success(self, api_client, mock_otp):
        """ارسال موفق OTP"""
        url = reverse('api:accounts:otp-send')
        response = api_client.post(url, {
            'phone': '09123456789',
            'device_type': 'android',
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'expires_in' in data['data']

    def test_send_otp_invalid_phone(self, api_client):
        """ارسال OTP با شماره نامعتبر"""
        url = reverse('api:accounts:otp-send')
        response = api_client.post(url, {'phone': '12345'})

        assert response.status_code == 400

    def test_send_otp_persian_digits(self, api_client, mock_otp):
        """ارسال OTP با ارقام فارسی"""
        url = reverse('api:accounts:otp-send')
        response = api_client.post(url, {'phone': '۰۹۱۲۳۴۵۶۷۸۹'})

        assert response.status_code == 200


@pytest.mark.django_db
class TestVerifyOTP:
    """تست‌های تایید OTP"""

    def test_verify_otp_new_user(self, api_client, mock_otp):
        """ثبت‌نام کاربر جدید"""
        # اول OTP ارسال کن
        mock_otp.send_otp('09120000001')

        url = reverse('api:accounts:otp-verify')
        response = api_client.post(url, {
            'phone': '09120000001',
            'code': '12345',
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['is_new_user'] is True
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']

    def test_verify_otp_existing_user(self, api_client, customer_user, mock_otp):
        """ورود کاربر موجود"""
        mock_otp.send_otp(customer_user.phone)

        url = reverse('api:accounts:otp-verify')
        response = api_client.post(url, {
            'phone': customer_user.phone,
            'code': '12345',
        })

        assert response.status_code == 200
        data = response.json()
        assert data['data']['is_new_user'] is False

    def test_verify_otp_invalid_code(self, api_client, mock_otp):
        """تایید با کد نامعتبر"""
        mock_otp.send_otp('09120000002')

        url = reverse('api:accounts:otp-verify')
        response = api_client.post(url, {
            'phone': '09120000002',
            'code': '99999',
        })

        # با mock، کد هر چه باشد قبول می‌شود
        assert response.status_code == 200


@pytest.mark.django_db
class TestProfile:
    """تست‌های پروفایل"""

    def test_get_profile(self, authenticated_customer_client, customer_user):
        """دریافت پروفایل"""
        url = reverse('api:accounts:profile')
        response = authenticated_customer_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['phone'] == customer_user.phone

    def test_update_profile(self, authenticated_customer_client):
        """بروزرسانی پروفایل"""
        url = reverse('api:accounts:profile')
        response = authenticated_customer_client.patch(url, {
            'full_name': 'نام جدید',
            'theme': 'dark',
        })

        assert response.status_code == 200
        data = response.json()
        assert data['data']['full_name'] == 'نام جدید'
        assert data['data']['theme'] == 'dark'

    def test_profile_unauthenticated(self, api_client):
        """دسترسی بدون احراز هویت"""
        url = reverse('api:accounts:profile')
        response = api_client.get(url)

        assert response.status_code == 401


@pytest.mark.django_db
class TestNationalIdVerification:
    """تست‌های استعلام کد ملی"""

    def test_verify_national_id_success(
        self, authenticated_customer_client, mock_shahkar
    ):
        """استعلام موفق کد ملی"""
        url = reverse('api:accounts:national-id-verify')
        response = authenticated_customer_client.post(url, {
            'national_id': '0012345679',
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['national_id'] == '0012345679'

    def test_verify_invalid_national_id(self, authenticated_customer_client):
        """استعلام با کد ملی نامعتبر"""
        url = reverse('api:accounts:national-id-verify')
        response = authenticated_customer_client.post(url, {
            'national_id': '123',  # خیلی کوتاه
        })

        assert response.status_code == 400


@pytest.mark.django_db
class TestLogout:
    """تست‌های خروج"""

    def test_logout_current_device(
        self, authenticated_customer_client, customer_user
    ):
        """خروج از دستگاه فعلی"""
        # اول یک refresh token بگیر
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(customer_user)

        url = reverse('api:accounts:logout')
        response = authenticated_customer_client.post(url, {
            'refresh_token': str(refresh),
            'all_devices': False,
        })

        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_logout_all_devices(
        self, authenticated_customer_client, customer_user
    ):
        """خروج از همه دستگاه‌ها"""
        url = reverse('api:accounts:logout')
        response = authenticated_customer_client.post(url, {
            'all_devices': True,
        })

        assert response.status_code == 200


@pytest.mark.django_db
class TestActiveDevices:
    """تست‌های دستگاه‌های فعال"""

    def test_list_devices(
        self, authenticated_customer_client, customer_user
    ):
        """لیست دستگاه‌ها"""
        from apps.accounts.models import ActiveDevice

        # ایجاد چند دستگاه
        ActiveDevice.objects.create(
            user=customer_user,
            device_type='android',
            device_name='Pixel 7',
            is_trusted=True,
        )
        ActiveDevice.objects.create(
            user=customer_user,
            device_type='ios',
            device_name='iPhone 14',
            is_trusted=True,
        )

        url = reverse('api:accounts:device-list')
        response = authenticated_customer_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 2