"""
تست‌های مدیریت خدمات
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.services.models import Service


@pytest.mark.django_db
class TestServiceList:
    """تست‌های لیست خدمات"""

    def test_list_services(
        self, authenticated_business_client, test_service
    ):
        """تست دریافت لیست خدمات"""
        url = reverse('services:service-list')
        response = authenticated_business_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True

    def test_list_services_unauthenticated(self, api_client):
        """بدون احراز هویت"""
        url = reverse('services:service-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestServiceCreate:
    """تست ایجاد خدمت"""

    def test_create_service_success(
        self,
        authenticated_business_client,
        approved_business,
        service_category,
        sub_service,
    ):
        """تست ایجاد خدمت جدید"""
        url = reverse('services:service-list')
        data = {
            'name': 'خدمت جدید',
            'category': service_category.id,
            'sub_service': sub_service.id,
            'original_price': 300000,
            'discount_percent': 15,
            'has_deposit': True,
            'deposit_amount': 50000,
            'duration': 45,
            'renewal_days': 7,
        }
        response = authenticated_business_client.post(
            url, data, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Service.objects.count() == 1

    def test_create_service_invalid_data(
        self, authenticated_business_client, approved_business
    ):
        """تست با داده‌های نامعتبر"""
        url = reverse('services:service-list')
        data = {
            'name': '',
            'original_price': -100,
        }
        response = authenticated_business_client.post(
            url, data, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestServiceDetail:
    """تست‌های جزئیات خدمت"""

    def test_get_service_detail(
        self, authenticated_business_client, test_service
    ):
        """دریافت جزئیات"""
        url = reverse(
            'services:service-detail',
            kwargs={'pk': test_service.id},
        )
        response = authenticated_business_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_update_service(
        self, authenticated_business_client, test_service
    ):
        """بروزرسانی خدمت"""
        url = reverse(
            'services:service-detail',
            kwargs={'pk': test_service.id},
        )
        data = {
            'name': 'نام جدید',
            'original_price': 600000,
        }
        response = authenticated_business_client.patch(
            url, data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        test_service.refresh_from_db()
        assert test_service.name == 'نام جدید'
        assert test_service.original_price == 600000

    def test_delete_service(
        self, authenticated_business_client, test_service
    ):
        """حذف خدمت"""
        url = reverse(
            'services:service-detail',
            kwargs={'pk': test_service.id},
        )
        response = authenticated_business_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Service.objects.count() == 0


@pytest.mark.django_db
class TestServiceToggle:
    """تست تغییر وضعیت"""

    def test_toggle_service_active(
        self, authenticated_business_client, test_service
    ):
        """تغییر فعال/غیرفعال"""
        assert test_service.is_active is True

        url = reverse(
            'services:service-toggle-active',
            kwargs={'pk': test_service.id},
        )
        response = authenticated_business_client.post(url)
        assert response.status_code == status.HTTP_200_OK

        test_service.refresh_from_db()
        assert test_service.is_active is False

    def test_toggle_back(
        self, authenticated_business_client, test_service
    ):
        """تغییر مجدد"""
        test_service.is_active = False
        test_service.save()

        url = reverse(
            'services:service-toggle-active',
            kwargs={'pk': test_service.id},
        )
        response = authenticated_business_client.post(url)
        assert response.status_code == status.HTTP_200_OK

        test_service.refresh_from_db()
        assert test_service.is_active is True


@pytest.mark.django_db
class TestServiceProperties:
    """تست property های مدل Service"""

    def test_discount_amount(self, test_service):
        assert test_service.discount_amount == 50000

    def test_final_price(self, test_service):
        assert test_service.final_price == 450000

    def test_app_fee(self, test_service):
        assert test_service.app_fee >= 10000

    def test_renewal_days(self, test_service):
        assert test_service.renewal_days == 30

    def test_duration(self, test_service):
        assert test_service.duration == 60