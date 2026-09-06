"""
Views برای دسته‌بندی‌ها
"""
from rest_framework.views import APIView
from rest_framework import permissions
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from apps.core.mixins import StandardResponseMixin
from apps.categories.models import ServiceCategory, BusinessCategory
from apps.categories.serializers import ServiceCategorySerializer, BusinessCategorySerializer


class ServiceCategoryListView(APIView, StandardResponseMixin):
    """لیست دسته‌بندی‌های خدمات — بدج تعداد با فیلتر مکانی"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=ServiceCategorySerializer(many=True),
        tags=['Categories'],
        summary='لیست دسته‌بندی‌های خدمات',
    )
    def get(self, request):
        categories = ServiceCategory.objects.filter(
            is_active=True,
            sub_services__is_active=True,
        )

        # ✅ فیلترهای مکانی — دقیقاً همان منطق BusinessListView
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
            business_count=Count(
                'services__business',
                filter=business_filter,
                distinct=True,
            )
        ).prefetch_related('sub_services').order_by('sort_order').distinct()

        serializer = ServiceCategorySerializer(categories, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': categories.count()},
        )