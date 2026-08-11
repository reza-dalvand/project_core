"""
سرویس جستجوی یکپارچه
"""
import logging
from django.db import connection
from django.db.models import Q

from apps.businesses.models import Business
from apps.services.models import Service
from apps.search.models import SearchHistory

logger = logging.getLogger(__name__)


def _is_postgres():
    """بررسی اینکه دیتابیس PostgreSQL است یا نه"""
    return connection.vendor == 'postgresql'


class SearchService:
    """سرویس جستجوی یکپارچه"""

    MAX_HISTORY_PER_USER = 50
    MIN_QUERY_LENGTH = 2

    @classmethod
    def search_businesses(cls, query, province_id=None, city_id=None,
                          category_id=None, min_rating=0, has_discount=False,
                          limit=20):
        """جستجو در کسب‌وکارها"""
        qs = Business.objects.filter(status=Business.Status.APPROVED)

        if province_id:
            qs = qs.filter(province_id=province_id)
        if city_id:
            qs = qs.filter(city_id=city_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if min_rating:
            qs = qs.filter(rating__gte=min_rating)
        if has_discount:
            qs = qs.filter(services__discount_percent__gt=0).distinct()

        if query and len(query) >= cls.MIN_QUERY_LENGTH:
            if _is_postgres():
                try:
                    from django.contrib.postgres.search import TrigramSimilarity
                    qs = qs.annotate(
                        similarity=TrigramSimilarity('name', query)
                    ).filter(similarity__gt=0.1).order_by('-similarity')
                except ImportError:
                    qs = qs.filter(
                        Q(name__icontains=query) | Q(about__icontains=query)
                    ).order_by('-rating', '-created_at')
            else:
                qs = qs.filter(
                    Q(name__icontains=query) | Q(about__icontains=query)
                ).order_by('-rating', '-created_at')
        else:
            qs = qs.order_by('-rating', '-created_at')

        return qs.select_related(
            'category', 'province', 'city', 'owner'
        )[:limit]

    @classmethod
    def search_services(cls, query, business_id=None, category_id=None,
                        min_price=0, max_price=None, has_discount=False,
                        limit=20):
        """جستجو در خدمات"""
        qs = Service.objects.filter(is_active=True)

        if business_id:
            qs = qs.filter(business_id=business_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if min_price:
            qs = qs.filter(original_price__gte=min_price)
        if max_price:
            qs = qs.filter(original_price__lte=max_price)
        if has_discount:
            qs = qs.filter(discount_percent__gt=0)

        if query and len(query) >= cls.MIN_QUERY_LENGTH:
            if _is_postgres():
                try:
                    from django.contrib.postgres.search import TrigramSimilarity
                    qs = qs.annotate(
                        similarity=TrigramSimilarity('name', query)
                    ).filter(similarity__gt=0.1).order_by('-similarity')
                except ImportError:
                    qs = qs.filter(
                        Q(name__icontains=query) | Q(description__icontains=query)
                    ).order_by('-created_at')
            else:
                qs = qs.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).order_by('-created_at')
        else:
            qs = qs.order_by('-created_at')

        return qs.select_related('business', 'category')[:limit]

    @classmethod
    def global_search(cls, query, user=None, limit_per_type=5):
        """جستجوی کلی"""
        if not query or len(query) < cls.MIN_QUERY_LENGTH:
            return {'businesses': [], 'services': [], 'total': 0}

        businesses = list(cls.search_businesses(query, limit=limit_per_type))
        services = list(cls.search_services(query, limit=limit_per_type))

        if user:
            cls._save_history(user, query, len(businesses) + len(services))

        return {
            'businesses': businesses,
            'services': services,
            'total': len(businesses) + len(services),
        }

    @classmethod
    def get_suggestions(cls, query, user=None, limit=10):
        """پیشنهادات جستجو (Autocomplete)"""
        if not query or len(query) < cls.MIN_QUERY_LENGTH:
            return []

        suggestions = set()

        businesses = Business.objects.filter(
            status=Business.Status.APPROVED,
            name__icontains=query,
        ).values_list('name', flat=True)[:5]
        suggestions.update(businesses)

        services = Service.objects.filter(
            is_active=True,
            name__icontains=query,
        ).values_list('name', flat=True)[:5]
        suggestions.update(services)

        if user:
            history = cls.get_user_history(user, limit=5)
            for h in history:
                if query.lower() in h['query'].lower():
                    suggestions.add(h['query'])

        return list(suggestions)[:limit]

    @classmethod
    def _save_history(cls, user, query, result_count):
        """ذخیره تاریخچه جستجو"""
        SearchHistory.objects.filter(
            user=user,
            query__iexact=query,
        ).delete()

        SearchHistory.objects.create(
            user=user,
            query=query,
            result_count=result_count,
        )

        # حذف رکوردهای اضافی
        keep_ids = list(
            SearchHistory.objects.filter(user=user)
            .order_by('-created_at')
            .values_list('id', flat=True)[:cls.MAX_HISTORY_PER_USER]
        )
        if keep_ids:
            SearchHistory.objects.filter(user=user).exclude(
                id__in=keep_ids
            ).delete()

    @classmethod
    def get_user_history(cls, user, limit=20):
        """دریافت تاریخچه جستجوی کاربر"""
        return list(
            SearchHistory.objects.filter(user=user)
            .order_by('-created_at')
            .values('id', 'query', 'result_count', 'created_at')[:limit]
        )

    @classmethod
    def clear_user_history(cls, user):
        """پاک کردن کل تاریخچه"""
        return SearchHistory.objects.filter(user=user).delete()