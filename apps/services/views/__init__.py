"""
Views برای مدیریت خدمات
"""
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.services.models import Service
from apps.services.serializers import (
    ServiceListSerializer,
    ServiceDetailSerializer,
    ServiceCreateSerializer,
    ServiceUpdateSerializer,
)


class ServiceListView(generics.ListCreateAPIView, StandardResponseMixin):
    """لیست و ایجاد خدمات"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceCreateSerializer
        return ServiceListSerializer

    def get_queryset(self):
        return Service.objects.filter(
            business__owner=self.request.user,
            business__is_active=True,
        ).select_related('category', 'sub_service', 'business').order_by('-created_at')

    @extend_schema(
        summary='لیست خدمات',
        tags=['Services'],
        responses={200: ServiceListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='ایجاد خدمت جدید',
        tags=['Services'],
        request=ServiceCreateSerializer,
        responses={201: ServiceDetailSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        business = self.request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        serializer.save(business=business)


class ServiceDetailView(generics.RetrieveUpdateDestroyAPIView, StandardResponseMixin):
    """جزئیات، بروزرسانی و حذف خدمت"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ServiceUpdateSerializer
        return ServiceDetailSerializer

    def get_queryset(self):
        qs = Service.objects.filter(
            business__owner=self.request.user,
            business__is_active=True,
        ).select_related('category', 'sub_service', 'business').order_by('-created_at')

        # ✅ فیلتر پیش‌فرض: فقط فعال‌ها
        show_inactive = self.request.query_params.get('show_inactive', '').lower()
        if show_inactive != 'true':
            qs = qs.filter(is_active=True)

        return qs

    @extend_schema(
        summary='جزئیات خدمت',
        tags=['Services'],
        responses={200: ServiceDetailSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی خدمت',
        tags=['Services'],
        request=ServiceUpdateSerializer,
        responses={200: ServiceDetailSerializer},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='حذف خدمت',
        tags=['Services'],
        responses={204: None},
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class ServiceToggleActiveView(APIView, StandardResponseMixin):
    """تغییر وضعیت فعال/غیرفعال خدمت"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        summary='تغییر وضعیت خدمت',
        tags=['Services'],
        responses={200: ServiceDetailSerializer},
    )
    def post(self, request, pk):
        service = get_object_or_404(
            Service,
            pk=pk,
            business__owner=request.user,
        )

        service.is_active = not service.is_active
        service.save()

        serializer = ServiceDetailSerializer(service, context={'request': request})
        return self.success_response(
            data=serializer.data,
            message=f'خدمت {service.name} {"فعال" if service.is_active else "غیرفعال"} شد',
        )