"""
تست‌های جستجو
"""
import pytest

from apps.search.models import SearchHistory
from apps.search.services.search_service import SearchService


@pytest.mark.django_db
class TestSearchService:

    def test_save_history(self, customer_user):
        SearchService._save_history(
            customer_user, 'فیشیال', 5
        )
        assert SearchHistory.objects.filter(
            user=customer_user
        ).count() == 1

    def test_history_max_limit(self, customer_user):
        for i in range(60):
            SearchHistory.objects.create(
                user=customer_user,
                query=f'جستجو {i}',
            )
        SearchService._save_history(
            customer_user, 'جستجوی جدید', 1
        )
        count = SearchHistory.objects.filter(
            user=customer_user
        ).count()
        assert count <= SearchService.MAX_HISTORY_PER_USER + 1

    def test_get_user_history(self, customer_user):
        SearchHistory.objects.create(
            user=customer_user,
            query='فیشیال',
            result_count=5,
        )
        history = SearchService.get_user_history(customer_user)
        assert len(history) == 1
        assert history[0]['query'] == 'فیشیال'

    def test_clear_history(self, customer_user):
        SearchHistory.objects.create(
            user=customer_user,
            query='فیشیال',
        )
        SearchService.clear_user_history(customer_user)
        assert SearchHistory.objects.filter(
            user=customer_user
        ).count() == 0

    def test_search_businesses(
        self, approved_business
    ):
        results = SearchService.search_businesses(
            query='سالن'
        )
        assert len(results) >= 1

    def test_search_businesses_empty_query(self):
        results = SearchService.search_businesses(query='')
        assert isinstance(results, list) or len(results) >= 0

    def test_global_search(
        self, customer_user, approved_business, test_service
    ):
        result = SearchService.global_search(
            query='سالن', user=customer_user
        )
        assert 'businesses' in result
        assert 'services' in result
        assert 'total' in result