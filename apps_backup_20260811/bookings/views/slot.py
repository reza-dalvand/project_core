"""
Views برای اسلات‌های زمانی
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.bookings.services.slot_service import SlotService
from apps.bookings.serializers.slot import (
    AvailableDateSerializer,
    AvailableSlotSerializer,
    SlotQuerySerializer,
    DateQuerySerializer,
)


class AvailableDatesView(APIView, StandardResponseMixin):
    """
    دریافت روزهای دارای اسلات آزاد

    GET /api/v1/bookings/available-dates/?service_id=X&days_ahead=30
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='service_id',
                type=int,
                required=True,
                description='شناسه خدمت',
            ),
            OpenApiParameter(
                name='days_ahead',
                type=int,
                required=False,
                description='تعداد روزهای آینده (پیش‌فرض: ۳۰)',
            ),
        ],
        responses={200: AvailableDateSerializer(many=True)},
        tags=['Booking - Slots'],
        summary='دریافت روزهای آزاد',
    )
    def get(self, request):
        serializer = DateQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data['service_id']
        days_ahead = serializer.validated_data.get('days_ahead', 30)

        # دریافت business_id از service
        from apps.businesses.models import Service
        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return self.error_response(
                message='خدمت مورد نظر یافت نشد',
                code='SERVICE_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        dates = SlotService.get_available_dates(
            business_id=service.business_id,
            service_id=service_id,
            days_ahead=days_ahead,
        )

        return self.success_response(
            data=AvailableDateSerializer(dates, many=True).data,
            meta={'count': len(dates)},
        )


class AvailableSlotsView(APIView, StandardResponseMixin):
    """
    دریافت اسلات‌های آزاد برای یک تاریخ خاص

    GET /api/v1/bookings/available-slots/?service_id=X&date=2026-08-01&employee_id=Y
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='service_id',
                type=int,
                required=True,
                description='شناسه خدمت',
            ),
            OpenApiParameter(
                name='date',
                type=str,
                required=True,
                description='تاریخ (YYYY-MM-DD)',
            ),
            OpenApiParameter(
                name='employee_id',
                type=int,
                required=False,
                description='شناسه کارمند (اختیاری)',
            ),
        ],
        responses={200: AvailableSlotSerializer(many=True)},
        tags=['Booking - Slots'],
        summary='دریافت ساعات آزاد',
    )
    def get(self, request):
        serializer = SlotQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data['service_id']
        target_date = serializer.validated_data['date']
        employee_id = serializer.validated_data.get('employee_id')

        # دریافت business_id از service
        from apps.businesses.models import Service
        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return self.error_response(
                message='خدمت مورد نظر یافت نشد',
                code='SERVICE_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        slots = SlotService.get_available_slots(
            business_id=service.business_id,
            service_id=service_id,
            target_date=target_date,
            employee_id=employee_id,
        )

        return self.success_response(
            data=AvailableSlotSerializer(slots, many=True).data,
            meta={'count': len(slots)},
        )