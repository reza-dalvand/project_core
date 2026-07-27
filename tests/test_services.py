"""
تست‌های مدیریت خدمات
"""
import pytest
from django.urls import reverse
from rest_framework import status
from apps.businesses.models import Service, Business, Category, Province, City


@pytest.fixture
def approved_business(api_client, business_owner_user):
    """ایجاد کسب‌وکار تایید شده"""
    province = Province.objects.create(name='تهران', slug='tehran')
    city = City.objects.create(name='تهران', slug='tehran-city', province=province)
    category = Category.objects.create(name='سالن زیبایی', slug='salon')

    business = Business.objects.create(
        owner=business_owner_user,
        name='سالن تست',
        category=category,
        province=province,
        city=city,
        address='آدرس تست',
        status='approved'
    )

    api_client.force_authenticate(user=business_owner_user)
    return business


@pytest.fixture
def service(approved_business):
    """ایجاد خدمت نمونه"""
    return Service.objects.create(
        business=approved_business,
        name='فیشیال تخصصی',
        original_price=500000,
        discount_percent=10,
        has_deposit=True,
        deposit_amount=100000,
        duration_minutes=60,
        is_active=True
    )


@pytest.mark.django_db
class TestServiceList:
    """تست‌های لیست خدمات"""

    def test_list_services_success(self, api_client, approved_business, service):
        """تست دریافت لیست خدمات"""
        url = reverse('api:businesses:service-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']) == 1

    def test_list_services_unauthenticated(self, api_client):
        """تست دریافت لیست خدمات بدون احراز هویت"""
        url = reverse('api:businesses:service-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_service_success(self, api_client, approved_business):
        """تست ایجاد خدمت جدید"""
        url = reverse('api:businesses:service-list')
        data = {
            'name': 'خدمت جدید',
            'original_price': 300000,
            'discount_percent': 15,
            'has_deposit': True,
            'deposit_amount': 50000,
            'duration_minutes': 45,
            'is_active': True,
            'reminder_days': 1
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert Service.objects.count() == 1

    def test_create_service_invalid_data(self, api_client, approved_business):
        """تست ایجاد خدمت با داده‌های نامعتبر"""
        url = reverse('api:businesses:service-list')
        data = {
            'name': '',  # نام خالی
            'original_price': -100,  # قیمت منفی
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False


@pytest.mark.django_db
class TestServiceDetail:
    """تست‌های جزئیات خدمت"""

    def test_get_service_detail(self, api_client, approved_business, service):
        """تست دریافت جزئیات خدمت"""
        url = reverse('api:businesses:service-detail', kwargs={'pk': service.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['name'] == service.name

    def test_update_service(self, api_client, approved_business, service):
        """تست بروزرسانی خدمت"""
        url = reverse('api:businesses:service-detail', kwargs={'pk': service.id})
        data = {
            'name': 'نام جدید',
            'original_price': 600000,
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        service.refresh_from_db()
        assert service.name == 'نام جدید'
        assert service.original_price == 600000

    def test_delete_service(self, api_client, approved_business, service):
        """تست حذف خدمت"""
        url = reverse('api:businesses:service-detail', kwargs={'pk': service.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Service.objects.count() == 0

    def test_toggle_service_active(self, api_client, approved_business, service):
        """تست تغییر وضعیت فعال/غیرفعال"""
        url = reverse('api:businesses:service-toggle-active', kwargs={'pk': service.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        service.refresh_from_db()
        assert service.is_active is False  # تغییر از True به False