"""
Views جستجوی پیشرفته
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.advanced.services.search_service import SearchService
from apps.advanced.serializers import (
    SearchQuerySerializer,
    SearchHistorySerializer,
    SuggestionSerializer,
)
from apps.businesses.serializers.business import (
    BusinessListSerializer,
    ServiceListSerializer,
)


class SearchView(APIView, StandardResponseMixin):
    """جستجوی کلی"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SearchQuerySerializer,
        tags=['Search'],
        summary='جستجوی پیشرفته',
        description='جستجو در کسب‌وکارها و خدمات',
    )
    def post(self, request):
        serializer = SearchQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        query = data['query']
        category = data.get('category', 'all')

        if category == 'businesses':
            businesses = SearchService.search_businesses(
                query=query,
                province_id=data.get('province_id'),
                city_id=data.get('city_id'),
                category_id=data.get('category_id'),
                min_rating=data.get('min_rating', 0),
                has_discount=data.get('has_discount', False),
                limit=data.get('limit', 20),
            )
            return self.success_response(
                data={
                    'businesses': BusinessListSerializer(
                        businesses, many=True, context={'request': request}
                    ).data,
                    'services': [],
                    'total': len(businesses),
                }
            )

        elif category == 'services':
            services = SearchService.search_services(
                query=query,
                category_id=data.get('category_id'),
                has_discount=data.get('has_discount', False),
                limit=data.get('limit', 20),
            )
            return self.success_response(
                data={
                    'businesses': [],
                    'services': ServiceListSerializer(
                        services, many=True, context={'request': request}
                    ).data,
                    'total': len(services),
                }
            )

        # جستجوی کلی
        results = SearchService.global_search(
            query=query,
            user=request.user,
            limit_per_type=data.get('limit', 10),
        )

        return self.success_response(
            data={
                'businesses': BusinessListSerializer(
                    results['businesses'],
                    many=True,
                    context={'request': request},
                ).data,
                'services': ServiceListSerializer(
                    results['services'],
                    many=True,
                    context={'request': request},
                ).data,
                'total': results['total'],
            }
        )


class SearchSuggestionsView(APIView, StandardResponseMixin):
    """پیشنهادات جستجو (Autocomplete)"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            {'name': 'q', 'type': str, 'required': True},
        ],
        responses=SuggestionSerializer(many=True),
        tags=['Search'],
        summary='پیشنهادات جستجو',
    )
    def get(self, request):
        query = request.query_params.get('q', '')

        if len(query) < 2:
            return self.success_response(data=[])

        suggestions = SearchService.get_suggestions(
            query=query,
            user=request.user,
        )

        return self.success_response(
            data=[{'suggestion': s} for s in suggestions]
        )


class SearchHistoryView(APIView, StandardResponseMixin):
    """تاریخچه جستجو"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=SearchHistorySerializer(many=True),
        tags=['Search'],
        summary='تاریخچه جستجوها',
    )
    def get(self, request):
        history = SearchService.get_user_history(request.user, limit=20)
        return self.success_response(data=history)

    @extend_schema(
        tags=['Search'],
        summary='پاک کردن تاریخچه',
    )
    def delete(self, request):
        SearchService.clear_user_history(request.user)
        return self.success_response(
            message='تاریخچه جستجو پاک شد'
        )


class SearchHistoryDeleteView(APIView, StandardResponseMixin):
    """حذف یک آیتم تاریخچه"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Search'],
        summary='حذف آیتم تاریخچه',
    )
    def delete(self, request, pk):
        from apps.advanced.models import SearchHistory

        deleted_count, _ = SearchHistory.objects.filter(
            id=pk,
            user=request.user,
        ).delete()

        if deleted_count:
            return self.success_response(message='آیتم حذف شد')

        return self.error_response(
            message='آیتم یافت نشد',
            status=status.HTTP_404_NOT_FOUND,
        )