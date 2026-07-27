"""
سرویس محاسبات جغرافیایی (Geolocation)
✅ بهینه‌شده: Haversine در Database به جای حلقه Python
"""
import math
from django.db import connection
from django.db.models import F, FloatField, ExpressionWrapper, Value, Q
from django.db.models.functions import ACos, Cos, Radians, Sin
from apps.businesses.models import Business


class GeolocationService:
    """سرویس محاسبات جغرافیایی"""
    EARTH_RADIUS_KM = 6371.0

    @classmethod
    def get_nearby_businesses(cls, latitude, longitude, radius_km=10,
                               category_id=None, limit=20):
        """
        ✅ بهینه: محاسبه فاصله در Database
        به جای حلقه Python روی تمام رکوردها
        """
        qs = Business.objects.filter(
            status=Business.Status.APPROVED,
            latitude__isnull=False,
            longitude__isnull=False,
        )

        if category_id:
            qs = qs.filter(category_id=category_id)

        # ✅ فیلتر bounding box اولیه (سریع - از index استفاده می‌کند)
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * math.cos(math.radians(latitude)))

        qs = qs.filter(
            latitude__range=(latitude - lat_delta, latitude + lat_delta),
            longitude__range=(longitude - lon_delta, longitude + lon_delta),
        )

        if connection.vendor == 'postgresql':
            # ✅ PostgreSQL: Haversine در Database
            qs = qs.annotate(
                distance=ExpressionWrapper(
                    ACos(
                        Cos(Radians(Value(latitude))) * Cos(Radians(F('latitude'))) *
                        Cos(Radians(F('longitude')) - Radians(Value(longitude))) +
                        Sin(Radians(Value(latitude))) * Sin(Radians(F('latitude')))
                    ) * Value(cls.EARTH_RADIUS_KM),
                    output_field=FloatField()
                )
            ).filter(
                distance__lte=radius_km
            ).order_by('distance')

            results = []
            for business in qs.select_related('category', 'city').only(
                'id', 'name', 'logo', 'rating_avg', 'rating_count',
                'latitude', 'longitude',
                'category__name', 'city__name',
            )[:limit]:
                results.append({
                    'business': business,
                    'distance': float(business.distance),
                    'distance_display': cls.format_distance(float(business.distance)),
                })
            return results
        else:
            # SQLite: محاسبه در Python (fallback)
            nearby = []
            for business in qs.select_related('category', 'city').only(
                'id', 'name', 'logo', 'rating_avg', 'rating_count',
                'latitude', 'longitude',
                'category__name', 'city__name',
            ):
                distance = cls.calculate_distance(
                    latitude, longitude,
                    float(business.latitude), float(business.longitude)
                )
                if distance <= radius_km:
                    nearby.append({
                        'business': business,
                        'distance': distance,
                        'distance_display': cls.format_distance(distance),
                    })

            nearby.sort(key=lambda x: x['distance'])
            return nearby[:limit]

    @classmethod
    def calculate_distance(cls, lat1, lon1, lat2, lon2):
        """محاسبه فاصله بین دو نقطه (Haversine formula)"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        return cls.EARTH_RADIUS_KM * c

    @classmethod
    def format_distance(cls, distance_km):
        """فرمت‌دهی فاصله برای نمایش"""
        if distance_km < 1:
            return f'{int(distance_km * 1000)} متر'
        elif distance_km < 10:
            return f'{distance_km:.1f} کیلومتر'
        else:
            return f'{int(distance_km)} کیلومتر'