"""
تست‌های ثبت کسب‌وکار — بدون role
"""
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model

from apps.businesses.models import Business

User = get_user_model()


@pytest.fixture
def create_test_image():
    """ایجاد تصویر تست"""
    def _create_image():
        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, 'JPEG')
        image_file.seek(0)
        return SimpleUploadedFile(
            name='test_image.jpg',
            content=image_file.read(),
            content_type='image/jpeg',
        )
    return _create_image


@pytest.mark.django_db
class TestLookupEndpoints:
    """تست endpoint های lookup"""

    def test_province_list(self, api_client, province):
        """تست لیست استان‌ها"""
        url = reverse('locations:province-list')
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) >= 1
        assert data['data'][0]['name'] == 'تهران'

    def test_city_list(self, api_client, province, city):
        """تست لیست شهرها"""
        url = reverse(
            'locations:city-list',
            kwargs={'province_id': province.id},
        )
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) >= 1
        assert data['data'][0]['name'] == 'تهران'

    def test_business_category_list(self, api_client, business_category):
        """تست لیست انواع کسب‌وکار"""
        url = reverse('categories:business-category-list')
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) >= 1


@pytest.mark.django_db
class TestBusinessCreation:
    """تست ایجاد کسب‌وکار"""

    def test_create_business_success(
        self,
        authenticated_customer_client,
        customer_user,
        business_category,
        province,
        city,
    ):
        """تست ایجاد موفق کسب‌وکار"""
        # ابتدا کد ملی کاربر را تایید می‌کنیم
        customer_user.is_national_id_verified = True
        customer_user.verified_name = 'کاربر تست'
        customer_user.save()

        url = reverse('businesses:business-create')
        data = {
            'name': 'سالن زیبایی تست',
            'category': business_category.id,
            'province': province.id,
            'city': city.id,
            'address': 'تهران، خیابان ولیعصر، پلاک ۱۲۳',
            'latitude': '35.7898',
            'longitude': '51.3768',
            'phone': '02112345678',
        }
        response = authenticated_customer_client.post(
            url, data, format='json'
        )
        assert response.status_code == 201
        resp_data = response.json()
        assert resp_data['success'] is True
        assert resp_data['data']['name'] == 'سالن زیبایی تست'
        assert resp_data['data']['status'] == 'pending'

        # بررسی ایجاد در دیتابیس
        assert Business.objects.count() == 1
        business = Business.objects.first()
        assert business.owner == customer_user

    def test_create_business_without_national_id(
        self,
        authenticated_customer_client,
        customer_user,
        business_category,
        province,
        city,
    ):
        """تست ایجاد بدون تایید کد ملی"""
        # کد ملی تایید نشده
        customer_user.is_national_id_verified = False
        customer_user.save()

        url = reverse('businesses:business-create')
        data = {
            'name': 'سالن تست',
            'category': business_category.id,
            'province': province.id,
            'city': city.id,
            'address': 'آدرس تست',
        }
        response = authenticated_customer_client.post(
            url, data, format='json'
        )
        assert response.status_code == 400

    def test_create_business_duplicate(
        self,
        authenticated_customer_client,
        approved_business,
        business_category,
        province,
        city,
    ):
        """تست ایجاد کسب‌وکار تکراری"""
        url = reverse('businesses:business-create')
        data = {
            'name': 'سالن دوم',
            'category': business_category.id,
            'province': province.id,
            'city': city.id,
            'address': 'آدرس تست ۲',
        }
        response = authenticated_customer_client.post(
            url, data, format='json'
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestBusinessStatus:
    """تست وضعیت کسب‌وکار"""

    def test_status_no_business(self, authenticated_customer_client):
        """وقتی کسب‌وکار ندارد"""
        url = reverse('businesses:business-status')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['has_business'] is False

    def test_status_with_business(
        self, authenticated_business_client, approved_business
    ):
        """وقتی کسب‌وکار دارد"""
        url = reverse('businesses:business-status')
        response = authenticated_business_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['has_business'] is True
        assert data['data']['business_id'] == approved_business.id
        assert data['data']['status'] == 'approved'


@pytest.mark.django_db
class TestBusinessDetail:
    """تست جزئیات کسب‌وکار"""

    def test_get_detail(
        self, authenticated_business_client, approved_business
    ):
        """دریافت جزئیات"""
        url = reverse('businesses:business-detail')
        response = authenticated_business_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['data']['name'] == 'سالن تست'

    def test_no_business_detail(
        self, authenticated_customer_client
    ):
        """کاربر بدون کسب‌وکار"""
        url = reverse('businesses:business-detail')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestPublicBusinessDetail:
    """تست جزئیات عمومی کسب‌وکار"""

    def test_public_detail(
        self, api_client, approved_business
    ):
        """مشاهده عمومی"""
        url = reverse(
            'businesses:public-business-detail',
            kwargs={'booking_slug': approved_business.booking_slug},
        )
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['data']['name'] == 'سالن تست'

    def test_public_detail_not_found(self, api_client):
        """کسب‌وکار ناموجود"""
        url = reverse(
            'businesses:public-business-detail',
            kwargs={'booking_slug': 'nonexistent'},
        )
        response = api_client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestBusinessDelete:
    """تست حذف کسب‌وکار"""

    def test_delete_business(
        self, authenticated_business_client, approved_business
    ):
        """حذف موفق"""
        url = reverse('businesses:business-delete')
        response = authenticated_business_client.delete(url)
        assert response.status_code == 200
        approved_business.refresh_from_db()
        assert approved_business.is_active is False

    def test_delete_with_active_appointments(
        self,
        authenticated_business_client,
        approved_business,
        test_appointment,
    ):
        """حذف با نوبت فعال"""
        url = reverse('businesses:business-delete')
        response = authenticated_business_client.delete(url)
        assert response.status_code == 400