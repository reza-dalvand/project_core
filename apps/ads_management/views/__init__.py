from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import models
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.ads_management.models import AdBanner
from apps.ads_management.serializers import AdBannerSerializer


class AdBannerListView(APIView, StandardResponseMixin):
    """
    دریافت لیست بنرهای اسلایدر فعال برای صفحه اصلی
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Ads Management'],
        summary='لیست بنرهای اسلایدر صفحه اصلی',
        responses={200: AdBannerSerializer(many=True)},
    )
    def get(self, request):
        now = timezone.now()
        qs = AdBanner.objects.filter(
            is_active=True,
        ).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now)
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gte=now)
        ).select_related('business')
        
        serializer = AdBannerSerializer(qs, many=True, context={'request': request})
        return self.success_response(data=serializer.data)