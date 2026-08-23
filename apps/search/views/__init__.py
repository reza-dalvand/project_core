"""
Views برای جستجوی یکپارچه — نسخه نهایی
"""
import logging
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q

from apps.core.mixins import StandardResponseMixin
from apps.search.models import SearchHistory
from apps.search.serializers import SearchHistorySerializer
from apps.search.services.search_service import SearchService

logger = logging.getLogger(__name__)


class GlobalSearchView(APIView, StandardResponseMixin):
    """جستجوی یکپارچه در کسب‌وکارها و خدمات"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='query', type=str, required=True,
                description='عبارت جستجو (حداقل ۲ کاراکتر)',
            ),
            OpenApiParameter(
                name='category', type=str, required=False,
                enum=['all', 'businesses', 'services'],
                description='دسته‌بندی جستجو',
            ),
            OpenApiParameter(
                name='limit', type=int, required=False,
                description='حداکثر تعداد نتایج',
            ),
        ],
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

        if category == 'businesses':
            businesses = list(SearchService.search_businesses(query, limit=limit))
            services = []
        elif category == 'services':
            businesses = []
            services = list(SearchService.search_services(query, limit=limit))
        else:
            businesses = list(SearchService.search_businesses(query, limit=limit))
            services = list(SearchService.search_services(query, limit=limit))

        total = len(businesses) + len(services)

        # ذخیره تاریخچه برای کاربران لاگین‌شده
        if request.user.is_authenticated:
            SearchService._save_history(request.user, query, total)

        # ✅ FIX فاز ۹: سریالایز کردن نتایج
        from apps.search.serializers import (
            SearchResultBusinessSerializer,
            SearchResultServiceSerializer,
        )

        businesses_data = SearchResultBusinessSerializer(
            businesses, many=True, context={'request': request}
        ).data
        services_data = SearchResultServiceSerializer(
            services, many=True, context={'request': request}
        ).data

        return self.success_response(
            data={
                'businesses': businesses_data,
                'services': services_data,
                'total': total,
                'query': query,
            },
        )

    
class SearchSuggestionsView(APIView, StandardResponseMixin):
    """پیشنهادات جستجو (Autocomplete)"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q', type=str, required=True,
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
    """
    تاریخچه جستجوی کاربر
    GET  → لیست تاریخچه
    DELETE → حذف کل تاریخچه یا یک آیتم خاص
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='limit', type=int, required=False,
                description='حداکثر تعداد نتایج (پیش‌فرض: ۲۰)',
            ),
        ],
        responses={200: SearchHistorySerializer(many=True)},
        tags=['Search'],
        summary='تاریخچه جستجو',
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 20))
        limit = max(1, min(limit, 50))

        history = SearchService.get_user_history(request.user, limit=limit)

        return self.success_response(
            data=history,
            meta={'count': len(history)},
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='id', type=int, required=False,
                description='شناسه آیتم برای حذف تکی (اگر ارسال نشود، همه حذف می‌شوند)',
            ),
        ],
        tags=['Search'],
        summary='حذف تاریخچه جستجو',
    )
    def delete(self, request):
        item_id = request.query_params.get('id')

        if item_id:
            # حذف یک آیتم خاص
            try:
                deleted_count, _ = SearchHistory.objects.filter(
                    id=int(item_id),
                    user=request.user,
                ).delete()

                if deleted_count == 0:
                    return self.error_response(
                        message='آیتم تاریخچه یافت نشد',
                        code='HISTORY_ITEM_NOT_FOUND',
                        status=status.HTTP_404_NOT_FOUND,
                    )

                return self.success_response(
                    message='آیتم تاریخچه حذف شد',
                )
            except (ValueError, TypeError):
                return self.error_response(
                    message='شناسه نامعتبر است',
                    code='INVALID_ID',
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # حذف کل تاریخچه
            SearchService.clear_user_history(request.user)
            return self.success_response(
                message='تاریخچه جستجو حذف شد',
            )

class NearbyView(APIView, StandardResponseMixin):
    """
    Endpoint ترکیبی Nearby
    کسب‌وکارها + مدلینگ + لاین را همزمان بر اساس فاصله برمی‌گرداند

    GET /search/nearby/?lat=&lng=&radius=10&category_id=
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='lat', type=float, required=True,
                description='عرض جغرافیایی کاربر',
            ),
            OpenApiParameter(
                name='lng', type=float, required=True,
                description='طول جغرافیایی کاربر',
            ),
            OpenApiParameter(
                name='radius', type=float, required=False,
                description='شعاع جستجو (کیلومتر، پیش‌فرض: ۱۰)',
            ),
            OpenApiParameter(
                name='category_id', type=int, required=False,
                description='فیلتر دسته‌بندی خدمات',
            ),
        ],
        tags=['Search'],
        summary='جستجوی نزدیک‌ترین‌ها (ترکیبی)',
    )
    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = float(request.query_params.get('radius', 10))
        category_id = request.query_params.get('category_id')

        if not lat or not lng:
            return self.error_response(
                message='پارامترهای lat و lng الزامی هستند',
                code='MISSING_LOCATION',
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat, lng = float(lat), float(lng)
            radius = max(0.5, min(radius, 50))  # بین ۰.۵ تا ۵۰ کیلومتر
        except (ValueError, TypeError):
            return self.error_response(
                message='مختصات جغرافیایی نامعتبر است',
                code='INVALID_COORDINATES',
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.gis.geos import Point
        from django.contrib.gis.measure import D

        from apps.businesses.models import Business
        from apps.ads.models import ModelRequest, LineRental
        from apps.businesses.serializers.business import BusinessListSerializer
        from apps.ads.serializers import ModelRequestListSerializer, LineRentalListSerializer

        point = Point(lng, lat, srid=4326)
        distance_filter = D(km=radius)

        # ─── کسب‌وکارهای نزدیک ───
        businesses = Business.objects.filter(
            status=Business.Status.APPROVED,
            is_active=True,
            location__distance_lte=(point, distance_filter),
        ).distance(point).order_by('distance')[:20]

        # فیلتر دسته‌بندی
        if category_id:
            businesses = businesses.filter(category_id=category_id)

        # ─── مدلینگ‌های نزدیک ───
        model_requests = ModelRequest.objects.filter(
            business__status='approved',
            business__is_active=True,
            location__distance_lte=(point, distance_filter),
        ).distance(point).order_by('distance')[:10]

        # ─── لاین‌های نزدیک ───
        line_rentals = LineRental.objects.filter(
            business__status='approved',
            business__is_active=True,
            location__distance_lte=(point, distance_filter),
        ).distance(point).order_by('distance')[:10]

        # سریالایز
        business_data = BusinessListSerializer(
            businesses, many=True, context={'request': request}
        ).data

        model_data = ModelRequestListSerializer(
            model_requests, many=True, context={'request': request}
        ).data

        line_data = LineRentalListSerializer(
            line_rentals, many=True, context={'request': request}
        ).data

        return self.success_response(
            data={
                'businesses': business_data,
                'model_requests': model_data,
                'line_rentals': line_data,
                'total': len(business_data) + len(model_data) + len(line_data),
            },
            meta={
                'lat': lat,
                'lng': lng,
                'radius_km': radius,
            },
        )