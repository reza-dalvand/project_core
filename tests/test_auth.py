"""
تست‌های احراز هویت — بدون role
"""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestSendOTP:
    def test_send_otp_success(self, api_client, mock_otp):
        url = reverse('accounts:otp-send')
        response = api_client.post(url, {'phone': '09123456789'})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['expires_in'] == 300
        assert data['data']['resend_after'] == 120

    def test_send_otp_invalid_phone(self, api_client):
        url = reverse('accounts:otp-send')
        response = api_client.post(url, {'phone': '12345'})
        assert response.status_code == 400

    def test_send_otp_missing_phone(self, api_client):
        url = reverse('accounts:otp-send')
        response = api_client.post(url, {})
        assert response.status_code == 400


@pytest.mark.django_db
class TestVerifyOTP:
    def test_verify_otp_new_user(self, api_client, mock_otp):
        mock_otp.send_otp('09120000001')
        url = reverse('accounts:otp-verify')
        response = api_client.post(url, {
            'phone': '09120000001',
            'code': '12345',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['data']['is_new_user'] is True
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert data['data']['user'] is not None

    def test_verify_otp_creates_user_without_role(self, api_client, mock_otp):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        mock_otp.send_otp('09120000002')
        url = reverse('accounts:otp-verify')
        api_client.post(url, {
            'phone': '09120000002',
            'code': '12345',
        })
        user = User.objects.filter(phone='09120000002').first()
        assert user is not None
        assert not hasattr(user, 'role')

    def test_verify_otp_invalid_code_format(self, api_client, mock_otp):
        url = reverse('accounts:otp-verify')
        response = api_client.post(url, {
            'phone': '09120000003',
            'code': '123',
        })
        assert response.status_code == 400

    def test_verify_otp_invalid_phone_format(self, api_client, mock_otp):
        url = reverse('accounts:otp-verify')
        response = api_client.post(url, {
            'phone': '012345',
            'code': '12345',
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_token_success(self, api_client, customer_user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(customer_user)
        url = reverse('accounts:token-refresh')
        response = api_client.post(url, {'refresh': str(refresh)})
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data

    def test_refresh_token_invalid(self, api_client):
        url = reverse('accounts:token-refresh')
        response = api_client.post(url, {'refresh': 'invalid_token'})
        assert response.status_code == 401


@pytest.mark.django_db
class TestProfile:
    def test_get_profile(self, authenticated_customer_client):
        url = reverse('accounts:profile')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        assert response.json()['success'] is True
        data = response.json()['data']
        assert data['phone'] == '09123456789'
        assert data['first_name'] == 'کاربر'

    def test_update_profile(self, authenticated_customer_client):
        url = reverse('accounts:profile')
        response = authenticated_customer_client.put(url, {
            'first_name': 'نام',
            'last_name': 'جدید',
        })
        assert response.status_code == 200

    def test_profile_unauthenticated(self, api_client):
        url = reverse('accounts:profile')
        response = api_client.get(url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestNationalId:
    def test_verify_national_id(self, authenticated_customer_client, mock_shahkar):
        url = reverse('accounts:national-id-verify')
        response = authenticated_customer_client.post(url, {
            'national_id': '0012345679',
        })
        assert response.status_code == 200

    def test_verify_national_id_invalid_format(self, authenticated_customer_client):
        url = reverse('accounts:national-id-verify')
        response = authenticated_customer_client.post(url, {
            'national_id': '123',
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogout:
    def test_logout(self, authenticated_customer_client):
        url = reverse('accounts:logout')
        response = authenticated_customer_client.post(url, {})
        assert response.status_code == 200

    def test_logout_unauthenticated(self, api_client):
        url = reverse('accounts:logout')
        response = api_client.post(url, {})
        assert response.status_code == 401


@pytest.mark.django_db
class TestDeleteAccount:
    def test_send_delete_otp(self, authenticated_customer_client, mock_otp):
        url = reverse('accounts:delete-account-send-otp')
        response = authenticated_customer_client.post(url, {})
        assert response.status_code == 200

    def test_delete_account(self, authenticated_customer_client, mock_otp):
        url = reverse('accounts:delete-account')
        response = authenticated_customer_client.post(url, {
            'confirmation_code': '12345',
        })
        assert response.status_code == 200
        # کاربر باید غیرفعال شده باشد
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=authenticated_customer_client.user.id)
        assert user.is_active is False


@pytest.mark.django_db
class TestDevices:
    def test_device_list(self, authenticated_customer_client):
        url = reverse('accounts:device-list')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200