"""
تست‌های علاقه‌مندی‌ها
"""
import pytest
from django.urls import reverse

from apps.favorites.models import FavoriteBusiness, FavoritePost


@pytest.mark.django_db
class TestFavoriteToggle:
    def test_toggle_favorite_business(
        self, authenticated_customer_client, approved_business
    ):
        url = reverse('favorites:favorite-toggle')
        response = authenticated_customer_client.post(url, {
            'favorite_type': 'business',
            'object_id': approved_business.id,
        }, format='json')
        assert response.status_code == 200
        assert response.json()['data']['is_favorited'] is True

    def test_toggle_favorite_post(
        self, authenticated_customer_client, approved_business
    ):
        from apps.explore.models import ExplorePost
        post = ExplorePost.objects.create(
            business=approved_business,
            caption='تست',
        )
        url = reverse('favorites:favorite-toggle')
        response = authenticated_customer_client.post(url, {
            'favorite_type': 'post',
            'object_id': post.id,
        }, format='json')
        assert response.status_code == 200


@pytest.mark.django_db
class TestFavoriteList:
    def test_favorite_list(
        self, authenticated_customer_client, customer_user, approved_business
    ):
        FavoriteBusiness.objects.create(
            user=customer_user,
            business=approved_business,
        )
        url = reverse('favorites:favorite-list')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200

    def test_favorite_count(
        self, authenticated_customer_client, customer_user, approved_business
    ):
        FavoriteBusiness.objects.create(
            user=customer_user,
            business=approved_business,
        )
        url = reverse('favorites:favorite-count')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        data = response.json()['data']
        assert data['total'] == 1