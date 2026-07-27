"""
Views برای مدیریت نوبت‌ها
"""
from datetime import datetime

from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsCustomer, IsBusinessOwner, IsApprovedBusinessOwner, IsBusinessOwnerOfObject
from apps.core.pagination import StandardResultsSetPagination
from apps.bookings.models import Appointment, CancellationRequest
from apps.bookings.serializers.booking import (
    AppointmentCreateSerializer,
    AppointmentListSerializer,
    AppointmentDetailSerializer,
    CancelBookingSerializer,
    CancelByBusinessSerializer,
    VerifyServiceCodeSerializer,
    CancellationRequestSerializer,
)
from apps.bookings.services.booking_service import (
    BookingService,
    BookingException,
    SlotNotAvailableException,
)


class CreateBookingView(APIView, StandardResponseMixin):
    """
    ایجاد نوبت جدید

    POST /api/v1/bookings/create/

    توجه: این endpoint فقط نوبت را رزرو می‌کند.
    پرداخت بیعانه از طریق Payment Gateway انجام می‌شود.
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    @extend_schema(
        request=AppointmentCreateSerializer,
        responses={201: AppointmentDetailSerializer},
        tags=['Booking'],
        summary='ایجاد نوبت',
        description='رزرو نوبت جدید (قبل از پرداخت بیعانه)',
    )
    def post(self, request):
        serializer = AppointmentCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        try:
            appointment = BookingService.create_booking(
                customer=request.user,
                service_id=serializer.validated_data['service_id'],
                target_date=serializer.validated_data['date'],
                start_time_str=serializer.validated_data['time'],
                employee_id=serializer.validated_data.get('employee_id'),
            )

            return self.success_response(
                data=AppointmentDetailSerializer(
                    appointment,
                    context={'request': request},
                ).data,
                message='نوبت با موفقیت رزرو شد. لطفاً بیعانه را پرداخت کنید.',
                status=status.HTTP_201_CREATED,
            )

        except BookingException as e:
            return e.as_response()
        except Exception as e:
            return self.error_response(
                message='خطا در رزرو نوبت',
                code='BOOKING_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CustomerAppointmentsView(ListAPIView, StandardResponseMixin):
    """
    لیست نوبت‌های مشتری

    GET /api/v1/bookings/my-appointments/?status=upcoming
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomer]
    serializer_class = AppointmentListSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                required=False,
                description='upcoming | past | all',
                enum=['upcoming', 'past', 'all'],
            ),
        ],
        responses={200: AppointmentListSerializer(many=True)},
        tags=['Booking - Customer'],
        summary='نوبت‌های من',
    )
    def get_queryset(self):
        from datetime import date

        qs = Appointment.objects.filter(
            customer=self.request.user,
        ).select_related('service', 'business', 'employee').order_by('-date', '-time')

        status_filter = self.request.query_params.get('status', 'all')
        today = date.today()

        if status_filter == 'upcoming':
            qs = qs.filter(
                date__gte=today,
                status__in=[
                    Appointment.Status.RESERVED,
                    Appointment.Status.CONFIRMED,
                ]
            )
        elif status_filter == 'past':
            qs = qs.filter(
                date__lt=today,
            ).exclude(
                status__in=[
                    Appointment.Status.RESERVED,
                    Appointment.Status.CONFIRMED,
                ]
            )

        return qs


class BusinessAppointmentsView(ListAPIView, StandardResponseMixin):
    """
    لیست نوبت‌های کسب‌وکار

    GET /api/v1/bookings/business-appointments/?status=reserved&date_filter=today
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    serializer_class = AppointmentDetailSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                required=False,
                enum=['all', 'reserved', 'cancelled', 'done'],
            ),
            OpenApiParameter(
                name='date_filter',
                type=str,
                required=False,
                enum=['today', 'week', 'month', 'all'],
            ),
            OpenApiParameter(
                name='search',
                type=str,
                required=False,
                description='جستجو در نام مشتری یا خدمت',
            ),
        ],
        responses={200: AppointmentDetailSerializer(many=True)},
        tags=['Booking - Business'],
        summary='نوبت‌های کسب‌وکار من',
    )
    def get_queryset(self):
        from datetime import date, timedelta

        business = self.request.user.business
        qs = Appointment.objects.filter(
            business=business,
        ).select_related('service', 'customer', 'employee').order_by('-date', '-time')

        # فیلتر وضعیت
        status_filter = self.request.query_params.get('status', 'all')
        if status_filter == 'reserved':
            qs = qs.filter(status=Appointment.Status.RESERVED)
        elif status_filter == 'cancelled':
            qs = qs.filter(status=Appointment.Status.CANCELLED_BY_SALON)
        elif status_filter == 'done':
            qs = qs.filter(status=Appointment.Status.DONE)

        # فیلتر تاریخ
        date_filter = self.request.query_params.get('date_filter', 'all')
        today = date.today()

        if date_filter == 'today':
            qs = qs.filter(date=today)
        elif date_filter == 'week':
            qs = qs.filter(date__gte=today, date__lte=today + timedelta(days=7))
        elif date_filter == 'month':
            qs = qs.filter(date__month=today.month, date__year=today.year)

        # جستجو
        search = self.request.query_params.get('search', '')
        if search:
            qs = qs.filter(
                Q(customer__full_name__icontains=search) |
                Q(service__name__icontains=search) |
                Q(customer__phone__icontains=search)
            )

        return qs


class AppointmentDetailView(RetrieveAPIView, StandardResponseMixin):
    """
    جزئیات نوبت

    GET /api/v1/bookings/<id>/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppointmentDetailSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related(
            'service', 'business', 'customer', 'employee'
        )

        # مشتری فقط نوبت‌های خودش را ببیند
        if user.role == 'customer':
            return qs.filter(customer=user)

        # صاحب کسب‌وکار فقط نوبت‌های کسب‌وکار خودش را ببیند
        if user.role == 'business_owner' and hasattr(user, 'business'):
            return qs.filter(business=user.business)

        return qs.none()

    @extend_schema(
        responses={200: AppointmentDetailSerializer},
        tags=['Booking'],
        summary='جزئیات نوبت',
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(data=serializer.data)


class CancelBookingView(APIView, StandardResponseMixin):
    """
    لغو نوبت توسط مشتری

    POST /api/v1/bookings/<id>/cancel/
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    @extend_schema(
        request=CancelBookingSerializer,
        responses={200: CancellationRequestSerializer},
        tags=['Booking - Customer'],
        summary='لغو نوبت',
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(
                id=pk,
                customer=request.user,
            )
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CancelBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cancellation = BookingService.cancel_by_customer(
                appointment=appointment,
                reason_text=serializer.validated_data.get('reason_text', ''),
            )

            return self.success_response(
                data=CancellationRequestSerializer(cancellation).data,
                message='نوبت با موفقیت لغو شد',
            )

        except BookingException as e:
            return e.as_response()


class CancelByBusinessView(APIView, StandardResponseMixin):
    """
    لغو نوبت توسط کسب‌وکار

    POST /api/v1/bookings/<id>/cancel-by-business/
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        request=CancelByBusinessSerializer,
        responses={200: CancellationRequestSerializer},
        tags=['Booking - Business'],
        summary='لغو نوبت توسط سالن',
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(
                id=pk,
                business=request.user.business,
            )
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CancelByBusinessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cancellation = BookingService.cancel_by_business(
                appointment=appointment,
                reason_text=serializer.validated_data['reason_text'],
                cancelled_by=request.user,
            )

            return self.success_response(
                data=CancellationRequestSerializer(cancellation).data,
                message='نوبت لغو شد. بیعانه + غرامت به مشتری مسترد می‌شود.',
            )

        except BookingException as e:
            return e.as_response()


class VerifyServiceCodeView(APIView, StandardResponseMixin):
    """
    تایید کد خدمت توسط سالن‌دار

    POST /api/v1/bookings/<id>/verify-code/
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        request=VerifyServiceCodeSerializer,
        tags=['Booking - Business'],
        summary='تایید انجام خدمت',
        description='وارد کردن کد ۴ رقمی مشتری برای تایید انجام خدمت و آزادسازی بیعانه',
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(
                id=pk,
                business=request.user.business,
            )
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VerifyServiceCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            success = BookingService.verify_service_code(
                appointment=appointment,
                entered_code=serializer.validated_data['code'],
                verified_by=request.user,
            )

            if success:
                return self.success_response(
                    data={
                        'appointment_id': appointment.id,
                        'status': appointment.status,
                        'verified_at': appointment.verified_at,
                    },
                    message='خدمت تایید شد. بیعانه به حساب شما واریز می‌شود.',
                )
            else:
                return self.error_response(
                    message='کد وارد شده صحیح نیست',
                    code='INVALID_CODE',
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except BookingException as e:
            return e.as_response()


class RegenerateCodeView(APIView, StandardResponseMixin):
    """
    تولید مجدد کد تایید (هر ۵ دقیقه)

    POST /api/v1/bookings/<id>/regenerate-code/
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    @extend_schema(
        tags=['Booking - Customer'],
        summary='تولید مجدد کد تایید',
        description='کد تایید ۴ رقمی جدید (هر ۵ دقیقه مجاز)',
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(
                id=pk,
                customer=request.user,
            )
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            new_code = BookingService.regenerate_verification_code(appointment)

            return self.success_response(
                data={
                    'verification_code': new_code,
                    'code_generated_at': appointment.code_generated_at,
                },
                message='کد تایید جدید تولید شد',
            )

        except BookingException as e:
            return e.as_response()


class AppointmentStatsView(APIView, StandardResponseMixin):
    """
    آمار نوبت‌های کسب‌وکار

    GET /api/v1/bookings/business-stats/
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Booking - Business'],
        summary='آمار نوبت‌ها',
    )
    def get(self, request):
        from datetime import date

        business = request.user.business
        today = date.today()

        appointments = Appointment.objects.filter(business=business)

        stats = {
            'total': appointments.count(),
            'reserved': appointments.filter(status=Appointment.Status.RESERVED).count(),
            'confirmed': appointments.filter(status=Appointment.Status.CONFIRMED).count(),
            'done': appointments.filter(status=Appointment.Status.DONE).count(),
            'cancelled': appointments.filter(
                status__in=[
                    Appointment.Status.CANCELLED_BY_CUSTOMER,
                    Appointment.Status.CANCELLED_BY_SALON,
                ]
            ).count(),
            'today': appointments.filter(date=today).count(),
            'upcoming': appointments.filter(
                date__gte=today,
                status__in=[
                    Appointment.Status.RESERVED,
                    Appointment.Status.CONFIRMED,
                ]
            ).count(),
        }

        return self.success_response(data=stats)