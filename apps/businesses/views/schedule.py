"""
Views برای مدیریت زمان‌بندی
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.businesses.models import Schedule, ScheduleBreak, Service
from apps.businesses.serializers.schedule import (
    ScheduleListSerializer,
    ScheduleDetailSerializer,
    ScheduleCreateUpdateSerializer,
    WeeklyScheduleSerializer,
)
from apps.core.permissions import IsApprovedBusinessOwner, IsBusinessOwnerOfObject
from apps.core.pagination import StandardResultsSetPagination


class ScheduleListView(generics.ListCreateAPIView):
    """
    لیست و ایجاد زمان‌بندی‌ها

    GET: دریافت لیست زمان‌بندی‌ها
    POST: ایجاد زمان‌بندی جدید
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ScheduleCreateUpdateSerializer
        return ScheduleListSerializer

    def get_queryset(self):
        """دریافت زمان‌بندی‌های کسب‌وکار فعلی"""
        queryset = Schedule.objects.filter(
            business=self.request.user.business
        ).prefetch_related('breaks').select_related('service')

        # فیلتر بر اساس خدمت
        service_id = self.request.query_params.get('service_id')
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        return queryset.order_by('service__name', 'weekday')

    @extend_schema(
        summary='لیست زمان‌بندی‌ها',
        description='دریافت لیست تمام زمان‌بندی‌های کسب‌وکار شما',
        parameters=[
            OpenApiParameter(
                name='service_id',
                type=int,
                description='فیلتر بر اساس شناسه خدمت',
                required=False,
            ),
        ],
        responses={200: ScheduleListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='ایجاد زمان‌بندی جدید',
        description='ایجاد یک زمان‌بندی جدید برای یک خدمت',
        request=ScheduleCreateUpdateSerializer,
        responses={201: ScheduleDetailSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    جزئیات، بروزرسانی و حذف زمان‌بندی

    GET: دریافت جزئیات زمان‌بندی
    PUT/PATCH: بروزرسانی زمان‌بندی
    DELETE: حذف زمان‌بندی
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner, IsBusinessOwnerOfObject]
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ScheduleCreateUpdateSerializer
        return ScheduleDetailSerializer

    def get_queryset(self):
        """دریافت زمان‌بندی‌های کسب‌وکار فعلی"""
        return Schedule.objects.filter(
            business=self.request.user.business
        ).prefetch_related('breaks').select_related('service')

    @extend_schema(
        summary='جزئیات زمان‌بندی',
        description='دریافت جزئیات کامل یک زمان‌بندی',
        responses={200: ScheduleDetailSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی زمان‌بندی',
        description='بروزرسانی اطلاعات یک زمان‌بندی',
        request=ScheduleCreateUpdateSerializer,
        responses={200: ScheduleDetailSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی جزئی زمان‌بندی',
        description='بروزرسانی بخشی از اطلاعات یک زمان‌بندی',
        request=ScheduleCreateUpdateSerializer,
        responses={200: ScheduleDetailSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary='حذف زمان‌بندی',
        description='حذف یک زمان‌بندی',
        responses={204: None}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class WeeklyScheduleView(APIView):
    """
    دریافت یا ذخیره زمان‌بندی هفتگی برای یک خدمت
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        summary='دریافت زمان‌بندی هفتگی',
        description='دریافت زمان‌بندی کامل یک هفته برای یک خدمت خاص',
        parameters=[
            OpenApiParameter(
                name='service_id',
                type=int,
                description='شناسه خدمت',
                required=True,
            ),
        ],
        responses={200: ScheduleListSerializer(many=True)}
    )
    def get(self, request):
        service_id = request.query_params.get('service_id')

        if not service_id:
            return Response({
                'success': False,
                'message': 'شناسه خدمت الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)

        # بررسی وجود خدمت
        service = get_object_or_404(
            Service,
            id=service_id,
            business=request.user.business
        )

        # دریافت زمان‌بندی‌های این خدمت
        schedules = Schedule.objects.filter(
            business=request.user.business,
            service=service
        ).prefetch_related('breaks').order_by('weekday')

        serializer = ScheduleListSerializer(schedules, many=True, context={'request': request})

        return Response({
            'success': True,
            'service_id': service.id,
            'service_name': service.name,
            'schedules': serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary='ذخیره زمان‌بندی هفتگی',
        description='ذخیره زمان‌بندی کامل یک هفته برای یک خدمت',
        request=WeeklyScheduleSerializer,
        responses={200: ScheduleListSerializer(many=True)}
    )
    @transaction.atomic
    def post(self, request):
        serializer = WeeklyScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data['service_id']
        schedules_data = serializer.validated_data['schedules']

        # بررسی وجود خدمت
        service = get_object_or_404(
            Service,
            id=service_id,
            business=request.user.business
        )

        # حذف زمان‌بندی‌های قبلی این خدمت
        Schedule.objects.filter(
            business=request.user.business,
            service=service
        ).delete()

        # ایجاد زمان‌بندی‌های جدید
        created_schedules = []
        for schedule_data in schedules_data:
            break_data = schedule_data.pop('break_data', [])
            schedule_data['business'] = request.user.business
            schedule_data['service'] = service

            schedule = Schedule.objects.create(**schedule_data)

            # ایجاد بازه‌های استراحت
            for break_item in break_data:
                ScheduleBreak.objects.create(schedule=schedule, **break_item)

            created_schedules.append(schedule)

        # بازگرداندن زمان‌بندی‌های ایجاد شده
        response_serializer = ScheduleListSerializer(
            created_schedules,
            many=True,
            context={'request': request}
        )

        return Response({
            'success': True,
            'message': f'{len(created_schedules)} زمان‌بندی با موفقیت ذخیره شد',
            'service_id': service.id,
            'service_name': service.name,
            'schedules': response_serializer.data
        }, status=status.HTTP_200_OK)