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

    def test_send_otp_invalid_phone(self, api_client):
        url = reverse('accounts:otp-send')
        response = api_client.post(url, {'phone': '12345'})
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


@pytest.mark.django_db
class TestProfile:
    def test_get_profile(self, authenticated_customer_client):
        url = reverse('accounts:profile')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_update_profile(self, authenticated_customer_client):
        url = reverse('accounts:profile')
        response = authenticated_customer_client.patch(url, {
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


@pytest.mark.django_db
class TestLogout:
    def test_logout(self, authenticated_customer_client):
        url = reverse('accounts:logout')
        response = authenticated_customer_client.post(url, {})
        assert response.status_code == 200