"""
Views برای زمان‌بندی — با تاریخ جلالی
"""
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from .models import ServiceSchedule
from .serializers import (
    ServiceScheduleSerializer,
    ServiceScheduleCreateSerializer,
    ServiceScheduleUpdateSerializer,
)


class ScheduleListView(generics.ListCreateAPIView, StandardResponseMixin):
    """لیست و ایجاد زمان‌بندی‌ها"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceScheduleCreateSerializer
        return ServiceScheduleSerializer

    def get_queryset(self):
        return ServiceSchedule.objects.filter(
            business__owner=self.request.user,
            business__is_active=True,
        ).select_related('service', 'business', 'team_member').order_by('jy', 'jm', 'jd')

    @extend_schema(
        summary='لیست زمان‌بندی‌ها',
        tags=['Schedules'],
        parameters=[
            OpenApiParameter(
                name='service_id',
                type=int,
                required=False,
                description='فیلتر بر اساس شناسه خدمت',
            ),
        ],
        responses={200: ServiceScheduleSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        service_id = request.query_params.get('service_id')
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='ایجاد زمان‌بندی جدید',
        tags=['Schedules'],
        request=ServiceScheduleCreateSerializer,
        responses={201: ServiceScheduleSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ScheduleDetailView(generics.RetrieveUpdateDestroyAPIView, StandardResponseMixin):
    """جزئیات، بروزرسانی و حذف زمان‌بندی"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ServiceScheduleUpdateSerializer
        return ServiceScheduleSerializer

    def get_queryset(self):
        return ServiceSchedule.objects.filter(
            business__owner=self.request.user,
            business__is_active=True,
        ).select_related('service', 'business', 'team_member')

    @extend_schema(
        summary='جزئیات زمان‌بندی',
        tags=['Schedules'],
        responses={200: ServiceScheduleSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی زمان‌بندی',
        tags=['Schedules'],
        request=ServiceScheduleUpdateSerializer,
        responses={200: ServiceScheduleSerializer},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='حذف زمان‌بندی',
        tags=['Schedules'],
        responses={204: None},
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class ScheduleByDateView(APIView, StandardResponseMixin):
    """دریافت زمان‌بندی‌ها برای یک تاریخ جلالی خاص"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='زمان‌بندی بر اساس تاریخ جلالی',
        tags=['Schedules'],
        parameters=[
            OpenApiParameter(name='jy', type=int, required=True, description='سال جلالی'),
            OpenApiParameter(name='jm', type=int, required=True, description='ماه جلالی'),
            OpenApiParameter(name='jd', type=int, required=True, description='روز جلالی'),
        ],
        responses={200: ServiceScheduleSerializer(many=True)},
    )
    def get(self, request):
        jy = request.query_params.get('jy')
        jm = request.query_params.get('jm')
        jd = request.query_params.get('jd')

        if not all([jy, jm, jd]):
            return self.error_response(
                message='پارامترهای jy, jm, jd الزامی هستند',
                code='MISSING_PARAMS',
            )

        schedules = ServiceSchedule.objects.filter(
            jy=jy, jm=jm, jd=jd,
            business__is_active=True,
            business__status='approved',
        ).select_related('service', 'business', 'team_member')

        # فیلتر بر اساس service_id
        service_id = request.query_params.get('service_id')
        if service_id:
            schedules = schedules.filter(service_id=service_id)

        serializer = ServiceScheduleSerializer(schedules, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': schedules.count()},
        )