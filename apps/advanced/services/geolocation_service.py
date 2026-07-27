"""
سرویس محاسبات جغرافیایی (Geolocation)
"""
import math
from django.db.models import F, FloatField, ExpressionWrapper
from django.db.models.functions import ACos, Cos, Radians, Sin

from apps.businesses.models import Business


class GeolocationService:
    """سرویس محاسبات جغرافیایی"""

    EARTH_RADIUS_KM = 6371.0

    @classmethod
    def get_nearby_businesses(cls, latitude, longitude, radius_km=10,
                              category_id=None, limit=20):
        """
        دریافت کسب‌وکارهای نزدیک با Haversine formula
        """
        # فیلتر اولیه
        qs = Business.objects.filter(
            status=Business.Status.APPROVED,
            latitude__isnull=False,
            longitude__isnull=False,
        )

        if category_id:
            qs = qs.filter(category_id=category_id)

        # محاسبه فاصله با Haversine (ساده‌شده برای SQLite)
        # در PostgreSQL می‌توان از PostGIS استفاده کرد
        nearby = []
        for business in qs.select_related('category', 'city'):
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

        # مرتب‌سازی بر اساس فاصله
        nearby.sort(key=lambda x: x['distance'])

        return nearby[:limit]

    @classmethod
    def calculate_distance(cls, lat1, lon1, lat2, lon2):
        """
        محاسبه فاصله بین دو نقطه (Haversine formula)
        Returns: فاصله به کیلومتر
        """
        # تبدیل به رادیان
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine
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