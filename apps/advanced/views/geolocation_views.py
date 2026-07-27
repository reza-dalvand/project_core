"""
Views جستجوی جغرافیایی
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.advanced.services.geolocation_service import GeolocationService
from apps.advanced.serializers import (
    NearbySearchSerializer,
    NearbyBusinessSerializer,
)


class NearbyBusinessesView(APIView, StandardResponseMixin):
    """کسب‌وکارهای نزدیک"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=NearbySearchSerializer,
        responses=NearbyBusinessSerializer(many=True),
        tags=['Geolocation'],
        summary='کسب‌وکارهای نزدیک',
        description='دریافت کسب‌وکارهای نزدیک به موقعیت جغرافیایی',
    )
    def post(self, request):
        serializer = NearbySearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        results = GeolocationService.get_nearby_businesses(
            latitude=data['latitude'],
            longitude=data['longitude'],
            radius_km=data.get('radius_km', 10),
            category_id=data.get('category_id'),
            limit=data.get('limit', 20),
        )

        # تبدیل به فرمت serializer
        serialized = []
        for item in results:
            business = item['business']
            serialized.append({
                'id': business.id,
                'name': business.name,
                'category_name': business.category.name if business.category else '',
                'city_name': business.city.name if business.city else '',
                'rating_avg': float(business.rating_avg or 0),
                'rating_count': business.rating_count or 0,
                'distance': round(item['distance'], 2),
                'distance_display': item['distance_display'],
                'logo': business.logo.url if business.logo else None,
            })

        return self.success_response(
            data=serialized,
            meta={'total': len(serialized)},
        )