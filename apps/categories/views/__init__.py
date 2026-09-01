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
    """لیست دسته‌بندی‌های خدمات — فقط دسته‌هایی که حداقل یک زیرخدمت فعال دارند"""
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
        ).annotate(
            # ✅ تعداد کسب‌وکارهای تاییدشده و فعال که حداقل یک خدمت فعال در این دسته دارند
            business_count=Count(
                'services__business',
                filter=Q(
                    services__is_active=True,
                    services__business__status='approved',
                    services__business__is_active=True,
                ),
                distinct=True,
            )
        ).prefetch_related('sub_services').order_by('sort_order').distinct()
        serializer = ServiceCategorySerializer(categories, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': categories.count()},
        )
    
class BusinessCategoryListView(APIView, StandardResponseMixin):
    """لیست انواع کسب‌وکار"""
    permission_classes = [permissions.AllowAny]
    @extend_schema(
    responses=BusinessCategorySerializer(many=True),
    tags=['Categories'],
    summary='لیست انواع کسب‌وکار',
    )
    def get(self, request):
        categories = BusinessCategory.objects.filter(is_active=True)
        serializer = BusinessCategorySerializer(categories, many=True)
        return self.success_response(
        data=serializer.data,
        meta={'count': categories.count()},
        )