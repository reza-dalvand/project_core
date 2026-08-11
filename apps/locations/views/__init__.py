"""
Views برای استان و شهر
"""
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework import permissions, status
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.locations.models import Province, City
from apps.locations.serializers import ProvinceSerializer, CitySerializer


class ProvinceListView(APIView, StandardResponseMixin):
    """لیست استان‌ها — با Cache"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=ProvinceSerializer(many=True),
        tags=['Locations'],
        summary='لیست استان‌ها',
    )
    def get(self, request):
        cache_key = 'provinces_list'
        provinces_data = cache.get(cache_key)

        if not provinces_data:
            provinces = Province.objects.filter(is_active=True).order_by('name')
            serializer = ProvinceSerializer(provinces, many=True)
            provinces_data = serializer.data
            cache.set(cache_key, provinces_data, timeout=86400)

        return self.success_response(
            data=provinces_data,
            meta={'count': len(provinces_data)},
        )


class CityListView(APIView, StandardResponseMixin):
    """لیست شهرهای یک استان — با Cache"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=CitySerializer(many=True),
        tags=['Locations'],
        summary='لیست شهرها',
    )
    def get(self, request, province_id):
        cache_key = f'cities_list_{province_id}'
        cities_data = cache.get(cache_key)

        if not cities_data:
            try:
                province = Province.objects.get(id=province_id)
            except Province.DoesNotExist:
                return self.error_response(
                    message='استان مورد نظر یافت نشد',
                    code='PROVINCE_NOT_FOUND',
                    status=status.HTTP_404_NOT_FOUND,
                )

            cities = City.objects.filter(
                province=province, is_active=True
            ).order_by('name')
            serializer = CitySerializer(cities, many=True)
            cities_data = serializer.data
            cache.set(cache_key, cities_data, timeout=86400)

        return self.success_response(
            data=cities_data,
            meta={'count': len(cities_data)},
        )