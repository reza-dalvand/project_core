"""
Views برای دسته‌بندی‌ها
"""
from rest_framework.views import APIView
from rest_framework import permissions
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.core.mixins import StandardResponseMixin
from apps.categories.models import ServiceCategory, BusinessCategory, SubService
from apps.categories.serializers import (
    ServiceCategorySerializer,
    BusinessCategorySerializer,
    SubServiceSerializer,
)


class ServiceCategoryListView(APIView, StandardResponseMixin):
    """... (همان کد قبلی بدون تغییر) ..."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        categories = ServiceCategory.objects.filter(
            is_active=True,
            sub_services__is_active=True,
        )
        province_id = request.query_params.get('province_id')
        city_id = request.query_params.get('city_id')
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius')

        business_filter = Q(
            services__is_active=True,
            services__business__status='approved',
            services__business__is_active=True,
        )
        if lat and lng:
            try:
                from django.contrib.gis.geos import Point
                from django.contrib.gis.measure import D
                lat, lng = float(lat), float(lng)
                radius_km = float(radius or 10)
                point = Point(lng, lat, srid=4326)
                business_filter &= Q(
                    services__business__location__isnull=False,
                    services__business__location__distance_lte=(point, D(km=radius_km)),
                )
            except (ValueError, TypeError):
                pass
        elif province_id:
            business_filter &= Q(services__business__province_id=province_id)
            if city_id:
                business_filter &= Q(services__business__city_id=city_id)

        categories = categories.annotate(
            business_count=Count('services__business', filter=business_filter, distinct=True)
        ).prefetch_related('sub_services').order_by('sort_order').distinct()

        serializer = ServiceCategorySerializer(categories, many=True)
        return self.success_response(data=serializer.data, meta={'count': len(serializer.data)})


# ═══════════════════════════════════════════════
#   🆕 لیست زیرخدمات (نوع خدمت) — فیکس فرم نمونه‌کار
# ═══════════════════════════════════════════════
class SubServiceListView(APIView, StandardResponseMixin):
    """
    لیست زیرخدمات فعال
    - بدون پارامتر: همه
    - با category_id (کوئری یا مسیر): فقط زیرخدمات همان دسته
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='category_id', type=int, required=False,
                             description='شناسه دسته‌بندی خدمات'),
        ],
        responses={200: SubServiceSerializer(many=True)},
        tags=['Categories'],
        summary='لیست زیرخدمات (نوع خدمت)',
    )
    def get(self, request, category_id=None):
        queryset = SubService.objects.filter(is_active=True).select_related('category')

        category_id = category_id or request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        queryset = queryset.order_by('category__sort_order', 'id')
        serializer = SubServiceSerializer(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': len(serializer.data)},
        )


# ═══════════════════════════════════════════════
#   🆕 لیست انواع کسب‌وکار (فیکس نگاشت اشتباه urls)
# ═══════════════════════════════════════════════
class BusinessCategoryListView(APIView, StandardResponseMixin):
    """لیست انواع کسب‌وکار (سالن، کلینیک و...)"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: BusinessCategorySerializer(many=True)},
        tags=['Categories'],
        summary='لیست انواع کسب‌وکار',
    )
    def get(self, request):
        queryset = BusinessCategory.objects.filter(is_active=True).order_by('id')
        serializer = BusinessCategorySerializer(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': len(serializer.data)},
        )