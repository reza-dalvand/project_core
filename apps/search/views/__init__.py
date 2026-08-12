"""
Views برای جستجوی یکپارچه
"""
import logging
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.search.models import SearchHistory
from apps.search.serializers import (
    GlobalSearchSerializer,
    GlobalSearchResponseSerializer,
    SearchSuggestionsSerializer,
    SearchHistorySerializer,
    SearchResultBusinessSerializer,
    SearchResultServiceSerializer,
)
from apps.search.services.search_service import SearchService

logger = logging.getLogger(__name__)


class GlobalSearchView(APIView, StandardResponseMixin):
    """جستجوی یکپارچه در کسب‌وکارها و خدمات"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='query',
                type=str,
                required=True,
                description='عبارت جستجو (حداقل ۲ کاراکتر)',
            ),
            OpenApiParameter(
                name='category',
                type=str,
                required=False,
                enum=['all', 'businesses', 'services'],
                description='دسته‌بندی جستجو',
            ),
            OpenApiParameter(
                name='limit',
                type=int,
                required=False,
                description='حداکثر تعداد نتایج',
            ),
        ],
        responses={200: GlobalSearchResponseSerializer},
        tags=['Search'],
        summary='جستجوی یکپارچه',
    )
    def get(self, request):
        query = request.query_params.get('query', '').strip()
        category = request.query_params.get('category', 'all')
        limit = int(request.query_params.get('limit', 10))

        if len(query) < SearchService.MIN_QUERY_LENGTH:
            return self.error_response(
                message='عبارت جستجو باید حداقل ۲ کاراکتر باشد',
                code='QUERY_TOO_SHORT',
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            limit = max(1, min(limit, 50))
        except (ValueError, TypeError):
            limit = 10

        # جستجو
        if category == 'businesses':
            businesses = list(
                SearchService.search_businesses(query, limit=limit)
            )
            services = []
        elif category == 'services':
            businesses = []
            services = list(
                SearchService.search_services(query, limit=limit)
            )
        else:
            businesses = list(
                SearchService.search_businesses(query, limit=limit)
            )
            services = list(
                SearchService.search_services(query, limit=limit)
            )

        total = len(businesses) + len(services)

        # ذخیره تاریخچه برای کاربران لاگین
        if request.user.is_authenticated:
            SearchService._save_history(request.user, query, total)

        # سریالایز نتایج
        business_data = SearchResultBusinessSerializer(
            businesses, many=True, context={'request': request}
        ).data
        service_data = SearchResultServiceSerializer(
            services, many=True, context={'request': request}
        ).data

        return self.success_response(
            data={
                'businesses': business_data,
                'services': service_data,
                'total': total,
                'query': query,
            },
            meta={
                'business_count': len(business_data),
                'service_count': len(service_data),
            },
        )


class SearchSuggestionsView(APIView, StandardResponseMixin):
    """پیشنهادات جستجو (Autocomplete)"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q',
                type=str,
                required=True,
                description='عبارت جستجو (حداقل ۲ کاراکتر)',
            ),
        ],
        tags=['Search'],
        summary='پیشنهادات جستجو',
    )
    def get(self, request):
        q = request.query_params.get('q', '').strip()

        if len(q) < SearchService.MIN_QUERY_LENGTH:
            return self.success_response(data=[])

        suggestions = SearchService.get_suggestions(
            query=q,
            user=request.user if request.user.is_authenticated else None,
            limit=10,
        )

        return self.success_response(data=suggestions)


class SearchHistoryView(APIView, StandardResponseMixin):
    """تاریخچه جستجوی کاربر"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Search'],
        summary='تاریخچه جستجو',
    )
    def get(self, request):
        history = SearchService.get_user_history(
            user=request.user,
            limit=20,
        )
        return self.success_response(
            data=history,
            meta={'count': len(history)},
        )

    @extend_schema(
        tags=['Search'],
        summary='حذف تاریخچه جستجو',
    )
    def delete(self, request):
        SearchService.clear_user_history(request.user)
        return self.success_response(
            message='تاریخچه جستجو حذف شد',
        )