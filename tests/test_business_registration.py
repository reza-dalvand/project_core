"""
تست‌های ثبت کسب‌وکار
"""
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model

from apps.bookings.models import Appointment
from apps.businesses.models import Business, Category, Province, City

User = get_user_model()


@pytest.fixture
def setup_lookup_data(db):
    """ایجاد داده‌های lookup (استان، شهر، دسته‌بندی)"""
    # ایجاد استان
    province = Province.objects.create(
        name='تهران',
        slug='tehran',
        order=1
    )

    # ایجاد شهر
    city = City.objects.create(
        name='تهران',
        slug='tehran-city',
        province=province,
        order=1
    )

    # ایجاد دسته‌بندی
    category = Category.objects.create(
        name='سالن زیبایی',
        slug='salon',
        icon='spa',
        color='#E91E63',
        order=1,
        is_active=True
    )

    return {
        'province': province,
        'city': city,
        'category': category
    }


@pytest.fixture
def verified_user(db):
    """کاربر تایید شده با کد ملی"""
    user = User.objects.create_user(
        phone='09123456789',
        role='customer',
        full_name='کاربر تست',
        is_verified=True,
        national_id='0012345679',
        national_id_verified=True,
        verified_name='کاربر تست'
    )
    return user


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
            content_type='image/jpeg'
        )

    return _create_image


@pytest.mark.django_db
class TestLookupEndpoints:
    """تست endpoint های lookup"""

    def test_province_list(self, api_client, verified_user, setup_lookup_data):
        """تست لیست استان‌ها"""
        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:province-list')
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'تهران'

    def test_city_list(self, api_client, verified_user, setup_lookup_data):
        """تست لیست شهرها"""
        api_client.force_authenticate(user=verified_user)
        province = setup_lookup_data['province']
        url = reverse('api:businesses:city-list', kwargs={'province_id': province.id})
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'تهران'

    def test_category_list(self, api_client, verified_user, setup_lookup_data):
        """تست لیست دسته‌بندی‌ها"""
        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:category-list')
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'سالن زیبایی'


@pytest.mark.django_db
class TestBusinessCreation:
    """تست ایجاد کسب‌وکار"""

    def test_create_business_success(self, api_client, verified_user, setup_lookup_data, create_test_image):
        """تست ایجاد موفق کسب‌وکار"""
        api_client.force_authenticate(user=verified_user)

        province = setup_lookup_data['province']
        city = setup_lookup_data['city']
        category = setup_lookup_data['category']

        url = reverse('api:businesses:business-create')
        data = {
            'name': 'سالن زیبایی تست',
            'category': category.id,
            'province': province.id,
            'city': city.id,
            'address': 'تهران، خیابان ولیعصر، پلاک ۱۲۳',
            'latitude': '35.7898',
            'longitude': '51.3768',
            'phone': '02112345678',
            'cover_image': create_test_image(),
            'owner_photo': create_test_image(),
        }

        response = api_client.post(url, data, format='multipart')

        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert data['data']['name'] == 'سالن زیبایی تست'
        assert data['data']['status'] == 'pending'

        # بررسی ایجاد کسب‌وکار در دیتابیس
        assert Business.objects.count() == 1
        business = Business.objects.first()
        assert business.owner == verified_user
        assert business.name == 'سالن زیبایی تست'

    def test_create_business_without_national_id_verification(self, api_client, db, setup_lookup_data):
        """تست ایجاد کسب‌وکار بدون تایید کد ملی"""
        user = User.objects.create_user(
            phone='09129876543',
            role='customer',
            is_verified=True,
            national_id_verified=False  # تایید نشده
        )
        api_client.force_authenticate(user=user)

        url = reverse('api:businesses:business-create')
        data = {
            'name': 'سالن زیبایی تست',
            'category': setup_lookup_data['category'].id,
            'province': setup_lookup_data['province'].id,
            'city': setup_lookup_data['city'].id,
            'address': 'تهران، خیابان ولیعصر، پلاک ۱۲۳',
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False

    def test_create_business_duplicate(self, api_client, verified_user, setup_lookup_data):
        """تست ایجاد کسب‌وکار تکراری"""
        # ایجاد اولین کسب‌وکار
        Business.objects.create(
            owner=verified_user,
            name='سالن اول',
            category=setup_lookup_data['category'],
            province=setup_lookup_data['province'],
            city=setup_lookup_data['city'],
            address='آدرس تست'
        )

        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:business-create')
        data = {
            'name': 'سالن دوم',
            'category': setup_lookup_data['category'].id,
            'province': setup_lookup_data['province'].id,
            'city': setup_lookup_data['city'].id,
            'address': 'آدرس تست ۲',
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False


@pytest.mark.django_db
class TestBusinessStatus:
    """تست وضعیت کسب‌وکار"""

    def test_business_status_no_business(self, api_client, verified_user):
        """تست وضعیت وقتی کسب‌وکار ندارد"""
        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:business-status')
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['has_business'] is False

    def test_business_status_with_business(self, api_client, verified_user, setup_lookup_data):
        """تست وضعیت وقتی کسب‌وکار دارد"""
        business = Business.objects.create(
            owner=verified_user,
            name='سالن تست',
            category=setup_lookup_data['category'],
            province=setup_lookup_data['province'],
            city=setup_lookup_data['city'],
            address='آدرس تست',
            status=Business.Status.PENDING
        )

        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:business-status')
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['has_business'] is True
        assert data['data']['business_id'] == business.id
        assert data['data']['status'] == 'pending'


@pytest.mark.django_db
class TestBusinessUpdate:
    """تست بروزرسانی کسب‌وکار"""

    def test_update_business_success(self, api_client, verified_user, setup_lookup_data):
        """تست بروزرسانی موفق کسب‌وکار"""
        business = Business.objects.create(
            owner=verified_user,
            name='سالن تست',
            category=setup_lookup_data['category'],
            province=setup_lookup_data['province'],
            city=setup_lookup_data['city'],
            address='آدرس تست',
            status=Business.Status.APPROVED  # تایید شده
        )

        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:business-detail')
        data = {
            'name': 'سالن تست بروزرسانی شده',
            'phone': '02198765432',
        }

        response = api_client.put(url, data, format='json')

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['name'] == 'سالن تست بروزرسانی شده'
        assert data['data']['phone'] == '02198765432'

    def test_update_pending_business_fails(self, api_client, verified_user, setup_lookup_data):
        """تست بروزرسانی کسب‌وکار در حال بررسی"""
        business = Business.objects.create(
            owner=verified_user,
            name='سالن تست',
            category=setup_lookup_data['category'],
            province=setup_lookup_data['province'],
            city=setup_lookup_data['city'],
            address='آدرس تست',
            status=Business.Status.PENDING  # در حال بررسی
        )

        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:business-detail')
        data = {
            'name': 'سالن تست بروزرسانی شده',
        }

        response = api_client.put(url, data, format='json')

        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False


@pytest.mark.django_db
class TestImageUpload:
    """تست آپلود تصاویر"""

    def test_upload_cover_image(self, api_client, verified_user, setup_lookup_data, create_test_image):
        """تست آپلود تصویر کاور"""
        business = Business.objects.create(
            owner=verified_user,
            name='سالن تست',
            category=setup_lookup_data['category'],
            province=setup_lookup_data['province'],
            city=setup_lookup_data['city'],
            address='آدرس تست'
        )

        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:upload-image')
        data = {
            'image': create_test_image(),
            'image_type': 'cover'
        }

        response = api_client.post(url, data, format='multipart')

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['image_type'] == 'cover'
        assert 'image_url' in data['data']

    def test_upload_invalid_image_type(self, api_client, verified_user, setup_lookup_data, create_test_image):
        """تست آپلود با نوع تصویر نامعتبر"""
        business = Business.objects.create(
            owner=verified_user,
            name='سالن تست',
            category=setup_lookup_data['category'],
            province=setup_lookup_data['province'],
            city=setup_lookup_data['city'],
            address='آدرس تست'
        )

        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:upload-image')
        data = {
            'image': create_test_image(),
            'image_type': 'invalid_type'
        }

        response = api_client.post(url, data, format='multipart')

        assert response.status_code == 400


@pytest.mark.django_db
class TestBusinessDelete:
    """تست حذف کسب‌وکار"""

    def test_delete_business_success(self, api_client, verified_user, setup_lookup_data):
        """تست حذف موفق کسب‌وکار"""
        business = Business.objects.create(
            owner=verified_user,
            name='سالن تست',
            category=setup_lookup_data['category'],
            province=setup_lookup_data['province'],
            city=setup_lookup_data['city'],
            address='آدرس تست'
        )

        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:business-delete')
        response = api_client.delete(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        # بررسی حذف از دیتابیس
        assert Business.objects.count() == 0

    def test_delete_business_with_active_appointments(self, api_client, verified_user, setup_lookup_data):
        """تست حذف کسب‌وکار با نوبت‌های فعال"""
        from apps.businesses.models import Service

        business = Business.objects.create(
            owner=verified_user,
            name='سالن تست',
            category=setup_lookup_data['category'],
            province=setup_lookup_data['province'],
            city=setup_lookup_data['city'],
            address='آدرس تست'
        )

        # ایجاد خدمت
        service = Service.objects.create(
            business=business,
            name='خدمت تست',
            original_price=100000,
            duration_minutes=60
        )

        # ایجاد نوبت فعال
        Appointment.objects.create(
            customer=verified_user,
            business=business,
            service=service,
            date='2026-08-01',
            time='10:00:00',
            status=Appointment.Status.RESERVED,
            original_price=100000,
            final_price=100000
        )

        api_client.force_authenticate(user=verified_user)
        url = reverse('api:businesses:business-delete')
        response = api_client.delete(url)

        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'ACTIVE_APPOINTMENTS' in data['error']['code']