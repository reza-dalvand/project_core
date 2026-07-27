"""
تست‌های ویژگی‌های پیشرفته
"""
import pytest
from django.urls import reverse

from apps.advanced.models import (
    SearchHistory, Favorite, ReferralCode, Referral
)
from apps.advanced.services.search_service import SearchService
from apps.advanced.services.favorite_service import FavoriteService
from apps.advanced.services.referral_service import ReferralService
from apps.advanced.services.geolocation_service import GeolocationService


@pytest.mark.django_db
class TestSearchService:
    def test_save_history(self, customer_user):
        SearchService._save_history(customer_user, 'فیشیال', 5)
        assert SearchHistory.objects.filter(user=customer_user).count() == 1

    def test_get_suggestions(self, customer_user):
        from apps.businesses.models import Business
        # ایجاد کسب‌وکار
        from apps.businesses.models import Category, Province, City
        cat = Category.objects.create(name='سالن')
        prov = Province.objects.create(name='تهران')
        city = City.objects.create(name='تهران', province=prov)

        Business.objects.create(
            name='سالن زیبایی نیلارام',
            category=cat,
            province=prov,
            city=city,
            owner=customer_user,
            status='approved',
            address='آدرس تست',
        )

        suggestions = SearchService.get_suggestions('نیلارام')
        assert len(suggestions) > 0


@pytest.mark.django_db
class TestFavoriteService:
    def test_toggle_favorite(self, customer_user):
        from apps.businesses.models import Business, Category, Province, City

        cat = Category.objects.create(name='سالن')
        prov = Province.objects.create(name='تهران')
        city = City.objects.create(name='تهران', province=prov)

        business = Business.objects.create(
            name='سالن تست',
            category=cat,
            province=prov,
            city=city,
            owner=customer_user,
            status='approved',
            address='آدرس',
        )

        # اضافه
        result = FavoriteService.toggle_favorite(
            customer_user, Favorite.Type.BUSINESS, business.id
        )
        assert result['is_favorited'] is True

        # حذف
        result = FavoriteService.toggle_favorite(
            customer_user, Favorite.Type.BUSINESS, business.id
        )
        assert result['is_favorited'] is False

    def test_is_favorited(self, customer_user):
        from apps.businesses.models import Business, Category, Province, City

        cat = Category.objects.create(name='سالن')
        prov = Province.objects.create(name='تهران')
        city = City.objects.create(name='تهران', province=prov)

        business = Business.objects.create(
            name='سالن',
            category=cat,
            province=prov,
            city=city,
            owner=customer_user,
            status='approved',
            address='آدرس',
        )

        FavoriteService.toggle_favorite(
            customer_user, Favorite.Type.BUSINESS, business.id
        )

        assert FavoriteService.is_favorited(
            customer_user, Favorite.Type.BUSINESS, business.id
        ) is True


@pytest.mark.django_db
class TestReferralService:
    def test_create_code(self, customer_user):
        code = ReferralService.get_or_create_code(customer_user)
        assert code.code.startswith('ZIBANO-')

    def test_apply_code(self, customer_user):
        referrer = customer_user
        code = ReferralService.get_or_create_code(referrer)

        referred = CustomUser.objects.create_user(
            phone='09121111111',
            is_verified=True,
        )

        result = ReferralService.apply_referral_code(code.code, referred)
        assert result['success'] is True

    def test_self_referral_rejected(self, customer_user):
        code = ReferralService.get_or_create_code(customer_user)
        result = ReferralService.apply_referral_code(code.code, customer_user)
        assert result['success'] is False


@pytest.mark.django_db
class TestGeolocationService:
    def test_calculate_distance(self):
        # تهران تا کرج ≈ 40km
        distance = GeolocationService.calculate_distance(
            35.6892, 51.3890,  # تهران
            35.8400, 50.9391,  # کرج
        )
        assert 30 < distance < 50

    def test_format_distance(self):
        assert 'متر' in GeolocationService.format_distance(0.5)
        assert 'کیلومتر' in GeolocationService.format_distance(5.5)


@pytest.mark.django_db
class TestSearchAPI:
    def test_search_api(self, authenticated_customer_client):
        url = reverse('api:advanced:search')
        response = authenticated_customer_client.post(url, {
            'query': 'فیشیال',
            'category': 'all',
        }, format='json')

        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_search_suggestions(self, authenticated_customer_client):
        url = reverse('api:advanced:search-suggestions')
        response = authenticated_customer_client.get(url, {'q': 'سالن'})

        assert response.status_code == 200

    def test_search_history(self, authenticated_customer_client):
        url = reverse('api:advanced:search-history')
        response = authenticated_customer_client.get(url)

        assert response.status_code == 200


@pytest.mark.django_db
class TestFavoriteAPI:
    def test_favorite_toggle(self, authenticated_customer_client):
        from apps.businesses.models import Business, Category, Province, City
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.first()

        cat = Category.objects.create(name='سالن')
        prov = Province.objects.create(name='تهران')
        city = City.objects.create(name='تهران', province=prov)

        business = Business.objects.create(
            name='تست',
            category=cat,
            province=prov,
            city=city,
            owner=user,
            status='approved',
            address='آدرس',
        )

        url = reverse('api:advanced:favorite-toggle')
        response = authenticated_customer_client.post(url, {
            'favorite_type': 'business',
            'object_id': business.id,
        }, format='json')

        assert response.status_code == 200
        assert response.json()['data']['is_favorited'] is True


@pytest.mark.django_db
class TestReferralAPI:
    def test_get_code(self, authenticated_customer_client):
        url = reverse('api:advanced:referral-code')
        response = authenticated_customer_client.get(url)

        assert response.status_code == 200
        assert response.json()['data']['code'].startswith('ZIBANO-')

    def test_get_stats(self, authenticated_customer_client):
        url = reverse('api:advanced:referral-stats')
        response = authenticated_customer_client.get(url)

        assert response.status_code == 200
        data = response.json()['data']
        assert 'total_referrals' in data
        assert 'referrer_reward' in data


@pytest.mark.django_db
class TestNearbyAPI:
    def test_nearby_businesses(self, authenticated_customer_client):
        url = reverse('api:advanced:nearby-businesses')
        response = authenticated_customer_client.post(url, {
            'latitude': 35.6892,
            'longitude': 51.3890,
            'radius_km': 10,
        }, format='json')

        assert response.status_code == 200
        assert response.json()['success'] is True


@pytest.mark.django_db
class TestReportsAPI:
    def test_create_report(self, authenticated_business_client, business_owner_user):
        from apps.businesses.models import Business, Category, Province, City

        cat = Category.objects.create(name='سالن')
        prov = Province.objects.create(name='تهران')
        city = City.objects.create(name='تهران', province=prov)

        Business.objects.create(
            name='سالن',
            category=cat,
            province=prov,
            city=city,
            owner=business_owner_user,
            status='approved',
            address='آدرس',
        )

        url = reverse('api:advanced:report-create')
        response = authenticated_business_client.post(url, {
            'report_type': 'transactions',
            'format': 'csv',
        }, format='json')

        assert response.status_code == 200