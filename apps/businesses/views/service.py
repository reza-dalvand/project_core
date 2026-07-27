"""
Views برای مدیریت خدمات کسب‌وکار
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404

from apps.businesses.models import Service
from apps.businesses.serializers.service import (
    ServiceListSerializer,
    ServiceDetailSerializer,
    ServiceCreateSerializer,
    ServiceUpdateSerializer,
)
from apps.core.permissions import IsApprovedBusinessOwner, IsBusinessOwnerOfObject
from apps.core.pagination import StandardResultsSetPagination
from django_filters.rest_framework import DjangoFilterBackend


class ServiceListView(generics.ListCreateAPIView):
    """
    لیست و ایجاد خدمات کسب‌وکار

    GET: دریافت لیست خدمات
    POST: ایجاد خدمت جدید
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceCreateSerializer
        return ServiceListSerializer

    def get_queryset(self):
        """دریافت خدمات کسب‌وکار فعلی"""
        return Service.objects.filter(
            business=self.request.user.business
        ).select_related('subcategory', 'subcategory__category').order_by('-created_at')

    @extend_schema(
        summary='لیست خدمات',
        description='دریافت لیست تمام خدمات کسب‌وکار شما',
        parameters=[
            OpenApiParameter(
                name='is_active',
                type=bool,
                description='فیلتر بر اساس وضعیت فعال/غیرفعال',
                required=False,
            ),
        ],
        responses={200: ServiceListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='ایجاد خدمت جدید',
        description='ایجاد یک خدمت جدید برای کسب‌وکار شما',
        request=ServiceCreateSerializer,
        responses={201: ServiceDetailSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    جزئیات، بروزرسانی و حذف خدمت

    GET: دریافت جزئیات خدمت
    PUT/PATCH: بروزرسانی خدمت
    DELETE: حذف خدمت
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner, IsBusinessOwnerOfObject]
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ServiceUpdateSerializer
        return ServiceDetailSerializer

    def get_queryset(self):
        """دریافت خدمات کسب‌وکار فعلی"""
        return Service.objects.filter(
            business=self.request.user.business
        ).select_related('subcategory', 'subcategory__category')

    @extend_schema(
        summary='جزئیات خدمت',
        description='دریافت جزئیات کامل یک خدمت',
        responses={200: ServiceDetailSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی خدمت',
        description='بروزرسانی اطلاعات یک خدمت',
        request=ServiceUpdateSerializer,
        responses={200: ServiceDetailSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی جزئی خدمت',
        description='بروزرسانی بخشی از اطلاعات یک خدمت',
        request=ServiceUpdateSerializer,
        responses={200: ServiceDetailSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary='حذف خدمت',
        description='حذف یک خدمت از کسب‌وکار',
        responses={204: None}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class ServiceToggleActiveView(APIView):
    """
    تغییر وضعیت فعال/غیرفعال خدمت
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        summary='تغییر وضعیت خدمت',
        description='فعال یا غیرفعال کردن یک خدمت',
        responses={200: ServiceDetailSerializer}
    )
    def post(self, request, pk):
        service = get_object_or_404(
            Service,
            pk=pk,
            business=request.user.business
        )

        service.is_active = not service.is_active
        service.save()

        serializer = ServiceDetailSerializer(service, context={'request': request})
        return Response({
            'success': True,
            'message': f'خدمت {service.name} {"فعال" if service.is_active else "غیرفعال"} شد',
            'data': serializer.data
        }, status=status.HTTP_200_OK)