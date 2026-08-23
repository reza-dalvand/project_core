"""
Views برای زمان‌بندی — نسخه نهایی (فاز ۴)
"""
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404
from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.schedules.models import ServiceSchedule
from apps.schedules.serializers import (
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
        ).select_related('service', 'business').order_by('jy', 'jm', 'jd')

    # ✅ اصلاح: اعتبارسنجی کسب‌وکار قبل از ایجاد
    def perform_create(self, serializer):
        serializer.save()

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
        ).select_related('service', 'business')

    # ✅ اصلاح: اعتبارسنجی مالکیت در بروزرسانی و حذف
    def perform_update(self, serializer):
        if serializer.instance.business.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('شما اجازه ویرایش این زمان‌بندی را ندارید')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.business.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('شما اجازه حذف این زمان‌بندی را ندارید')
        instance.delete()

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
            OpenApiParameter(name='jy', type=int, required=True),
            OpenApiParameter(name='jm', type=int, required=True),
            OpenApiParameter(name='jd', type=int, required=True),
            OpenApiParameter(name='service_id', type=int, required=False),
            # ✅ جدید: فیلتر کسب‌وکار
            OpenApiParameter(name='business_id', type=int, required=False),
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
        ).select_related('service', 'business')

        service_id = request.query_params.get('service_id')
        if service_id:
            schedules = schedules.filter(service_id=service_id)

        # ✅ جدید: فیلتر کسب‌وکار
        business_id = request.query_params.get('business_id')
        if business_id:
            schedules = schedules.filter(business_id=business_id)

        serializer = ServiceScheduleSerializer(schedules, many=True)

        return self.success_response(
            data=serializer.data,
            meta={'count': schedules.count()},
        )


class AvailableSlotsView(APIView, StandardResponseMixin):
    """
    دریافت اسلات‌های آزاد برای یک تاریخ جلالی خاص
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='اسلات‌های آزاد برای رزرو',
        tags=['Schedules'],
        parameters=[
            OpenApiParameter(name='business_id', type=int, required=True),
            OpenApiParameter(name='service_id', type=int, required=True),
            OpenApiParameter(name='jy', type=int, required=True),
            OpenApiParameter(name='jm', type=int, required=True),
            OpenApiParameter(name='jd', type=int, required=True),
        ],
    )
    def get(self, request):
        business_id = request.query_params.get('business_id')
        service_id = request.query_params.get('service_id')
        jy = request.query_params.get('jy')
        jm = request.query_params.get('jm')
        jd = request.query_params.get('jd')

        if not all([business_id, service_id, jy, jm, jd]):
            return self.error_response(
                message='پارامترهای business_id, service_id, jy, jm, jd الزامی هستند',
                code='MISSING_PARAMS',
            )

        try:
            business_id = int(business_id)
            service_id = int(service_id)
            jy = int(jy)
            jm = int(jm)
            jd = int(jd)
        except (ValueError, TypeError):
            return self.error_response(
                message='پارامترها باید عددی باشند',
                code='INVALID_PARAMS',
            )

        if not (1 <= jm <= 12) or not (1 <= jd <= 31):
            return self.error_response(
                message='تاریخ جلالی نامعتبر است',
                code='INVALID_DATE',
            )

        from apps.appointments.services.slot_service import SlotService

        slots = SlotService.get_available_slots(
            business_id=business_id,
            service_id=service_id,
            jy=jy,
            jm=jm,
            jd=jd,
        )

        return self.success_response(
            data=slots,
            meta={'count': len(slots)},
        )


class AvailableDatesView(APIView, StandardResponseMixin):
    """
    دریافت روزهای دارای اسلات آزاد
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='روزهای دارای اسلات آزاد',
        tags=['Schedules'],
        parameters=[
            OpenApiParameter(name='business_id', type=int, required=True),
            OpenApiParameter(name='service_id', type=int, required=True),
            OpenApiParameter(
                name='days_ahead',
                type=int,
                required=False,
                description='تعداد روزهای آینده (پیش‌فرض: ۳۰)',
            ),
        ],
    )
    def get(self, request):
        business_id = request.query_params.get('business_id')
        service_id = request.query_params.get('service_id')
        days_ahead = request.query_params.get('days_ahead', '30')

        if not all([business_id, service_id]):
            return self.error_response(
                message='پارامترهای business_id و service_id الزامی هستند',
                code='MISSING_PARAMS',
            )

        try:
            business_id = int(business_id)
            service_id = int(service_id)
            days_ahead = min(int(days_ahead), 60)
            days_ahead = max(days_ahead, 1)
        except (ValueError, TypeError):
            return self.error_response(
                message='پارامترها باید عددی باشند',
                code='INVALID_PARAMS',
            )

        from apps.appointments.services.slot_service import SlotService

        dates = SlotService.get_available_dates(
            business_id=business_id,
            service_id=service_id,
            days_ahead=days_ahead,
        )

        return self.success_response(
            data=dates,
            meta={'count': len(dates)},
        )