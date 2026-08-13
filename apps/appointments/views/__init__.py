"""
Views برای مدیریت نوبت‌ها — با تاریخ جلالی
"""
import logging
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.appointments.models import Appointment
from apps.appointments.serializers import (
    AppointmentCreateSerializer,
    AppointmentListSerializer,
    AppointmentDetailSerializer,
    CancelAppointmentSerializer,
    VerifyServiceCodeSerializer,
)
from apps.appointments.services.booking_service import BookingService, BookingException

logger = logging.getLogger(__name__)


class CreateAppointmentView(APIView, StandardResponseMixin):
    """ایجاد نوبت جدید"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=AppointmentCreateSerializer,
        responses={201: AppointmentDetailSerializer},
        tags=['Appointments'],
        summary='ایجاد نوبت',
    )
    def post(self, request):
        serializer = AppointmentCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        try:
            appointment = BookingService.create_appointment(
                customer=request.user,
                service_id=serializer.validated_data['service_id'],
                jy=serializer.validated_data['jy'],
                jm=serializer.validated_data['jm'],
                jd=serializer.validated_data['jd'],
                time_slot_str=serializer.validated_data['time_slot'],
            )

            return self.success_response(
                data=AppointmentDetailSerializer(
                    appointment, context={'request': request}
                ).data,
                message='نوبت با موفقیت رزرو شد. لطفاً بیعانه را پرداخت کنید.',
                status=status.HTTP_201_CREATED,
            )
        except BookingException as e:
            return e.as_response()
        except Exception as e:
            logger.exception(f"Create appointment error: {e}")
            return self.error_response(
                message='خطا در رزرو نوبت',
                code='BOOKING_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CustomerAppointmentsView(generics.ListAPIView, StandardResponseMixin):
    """لیست نوبت‌های مشتری"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppointmentListSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                required=False,
                enum=['upcoming', 'past', 'all'],
            ),
        ],
        tags=['Appointments - Customer'],
        summary='نوبت‌های من',
    )
    def get_queryset(self):
        from apps.core.utils import today_jalali_key

        qs = Appointment.objects.filter(
            customer=self.request.user,
        ).select_related('service', 'business').order_by('-jy', '-jm', '-jd', 'time_slot')

        status_filter = self.request.query_params.get('status', 'all')
        today_key = today_jalali_key()

        if status_filter == 'upcoming':
            qs = qs.filter(
                date_key__gte=today_key,
                status=Appointment.Status.RESERVED,
            )
        elif status_filter == 'past':
            qs = qs.filter(date_key__lt=today_key)

        return qs


class BusinessAppointmentsView(generics.ListAPIView, StandardResponseMixin):
    """لیست نوبت‌های کسب‌وکار با فیلترهای پیشرفته"""
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
                description='فیلتر وضعیت',
            ),
            OpenApiParameter(
                name='search',
                type=str,
                required=False,
                description='جستجو در نام مشتری، شماره تلفن یا خدمت',
            ),
            # 🆕 فاز ۴: فیلتر تاریخ
            OpenApiParameter(
                name='date_filter',
                type=str,
                required=False,
                enum=['today', 'week', 'month', 'all'],
                description='فیلتر بازه زمانی',
            ),
            OpenApiParameter(
                name='date_from',
                type=str,
                required=False,
                description='تاریخ شروع (فرمت: 1405/04/01)',
            ),
            OpenApiParameter(
                name='date_to',
                type=str,
                required=False,
                description='تاریخ پایان (فرمت: 1405/04/31)',
            ),
        ],
        tags=['Appointments - Business'],
        summary='نوبت‌های کسب‌وکار من',
    )
    def get_queryset(self):
        import jdatetime

        business = self.request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        qs = Appointment.objects.filter(
            business=business,
        ).select_related('service', 'customer').order_by(
            '-jy', '-jm', '-jd', 'time_slot'
        )

        # ─── فیلتر وضعیت ───
        status_filter = self.request.query_params.get('status', 'all')
        if status_filter == 'reserved':
            qs = qs.filter(status=Appointment.Status.RESERVED)
        elif status_filter == 'cancelled':
            qs = qs.filter(
                status__in=[
                    Appointment.Status.CANCELLED_BY_SALON,
                    Appointment.Status.CANCELLED_BY_CUSTOMER,
                ]
            )
        elif status_filter == 'done':
            qs = qs.filter(status=Appointment.Status.DONE)

        # ─── 🆕 فاز ۴: فیلتر بازه زمانی ───
        date_filter = self.request.query_params.get('date_filter')

        if date_filter:
            today = jdatetime.date.today()
            today_key = f'{today.jyear}/{today.jmonth:02d}/{today.jday:02d}'

            if date_filter == 'today':
                qs = qs.filter(date_key=today_key)

            elif date_filter == 'week':
                # ۷ روز آینده
                week_end = today + jdatetime.timedelta(days=7)
                week_end_key = f'{week_end.jyear}/{week_end.jmonth:02d}/{week_end.jday:02d}'
                qs = qs.filter(date_key__gte=today_key, date_key__lte=week_end_key)

            elif date_filter == 'month':
                # ماه جاری
                month_start = jdatetime.date(today.jyear, today.jmonth, 1)
                month_start_key = f'{month_start.jyear}/{month_start.jmonth:02d}/01'

                # محاسبه پایان ماه
                if today.jmonth == 12:
                    next_month = jdatetime.date(today.jyear + 1, 1, 1)
                else:
                    next_month = jdatetime.date(today.jyear, today.jmonth + 1, 1)
                month_end = next_month - jdatetime.timedelta(days=1)
                month_end_key = f'{month_end.jyear}/{month_end.jmonth:02d}/{month_end.jday:02d}'

                qs = qs.filter(date_key__gte=month_start_key, date_key__lte=month_end_key)

            # 'all' → هیچ فیلتری اعمال نمی‌شود

        # ─── 🆕 فاز ۴: فیلتر بازه دلخواه ───
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            qs = qs.filter(date_key__gte=date_from)
        if date_to:
            qs = qs.filter(date_key__lte=date_to)

        # ─── جستجو ───
        search = self.request.query_params.get('search', '')
        if search:
            qs = qs.filter(
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(customer__phone__icontains=search) |
                Q(service__name__icontains=search)
            )

        return qs

    
class AppointmentDetailView(generics.RetrieveAPIView, StandardResponseMixin):
    """جزئیات نوبت"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppointmentDetailSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related(
            'service', 'business', 'customer'
        )

        if user.is_authenticated:
            user_business = user.businesses.filter(is_active=True).first()
            if user_business:
                return qs.filter(
                    Q(customer=user) | Q(business=user_business)
                )
            return qs.filter(customer=user)

        return qs.none()

    @extend_schema(
        responses={200: AppointmentDetailSerializer},
        tags=['Appointments'],
        summary='جزئیات نوبت',
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(data=serializer.data)


class CancelAppointmentView(APIView, StandardResponseMixin):
    """لغو نوبت توسط مشتری"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=CancelAppointmentSerializer,
        tags=['Appointments - Customer'],
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

        serializer = CancelAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            BookingService.cancel_by_customer(
                appointment=appointment,
                reason_text=serializer.validated_data.get('reason_text', ''),
            )
            return self.success_response(
                message='نوبت با موفقیت لغو شد. بیعانه ظرف ۴۸ ساعت به حساب شما واریز می‌شود.',
            )
        except BookingException as e:
            return e.as_response()

        
class CancelByBusinessView(APIView, StandardResponseMixin):
    """لغو نوبت توسط کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        request=CancelAppointmentSerializer,
        tags=['Appointments - Business'],
        summary='لغو نوبت توسط سالن',
    )
    def post(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        try:
            appointment = Appointment.objects.get(
                id=pk,
                business=business,
            )
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CancelAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            appointment.cancel_by_salon(
                reason=serializer.validated_data.get('reason_text', ''),
            )

            return self.success_response(
                message='نوبت لغو شد. بیعانه به مشتری مسترد می‌شود.',
            )
        except BookingException as e:
            return e.as_response()


class VerifyServiceCodeView(APIView, StandardResponseMixin):
    """تایید کد خدمت توسط سالن‌دار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        request=VerifyServiceCodeSerializer,
        tags=['Appointments - Business'],
        summary='تایید انجام خدمت',
    )
    def post(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        try:
            appointment = Appointment.objects.get(
                id=pk,
                business=business,
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
    """تولید مجدد کد تایید"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Appointments - Customer'],
        summary='تولید مجدد کد تایید',
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
                },
                message='کد تایید جدید تولید شد',
            )
        except BookingException as e:
            return e.as_response()


class AppointmentStatsView(APIView, StandardResponseMixin):
    """آمار نوبت‌های کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Appointments - Business'],
        summary='آمار نوبت‌ها',
    )
    def get(self, request):
        from apps.core.utils import today_jalali_key

        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        today_key = today_jalali_key()
        appointments = Appointment.objects.filter(business=business)

        stats = {
            'total': appointments.count(),
            'reserved': appointments.filter(status=Appointment.Status.RESERVED).count(),
            'done': appointments.filter(status=Appointment.Status.DONE).count(),
            'cancelled': appointments.filter(
                status__in=[
                    Appointment.Status.CANCELLED_BY_CUSTOMER,
                    Appointment.Status.CANCELLED_BY_SALON,
                ]
            ).count(),
            'today': appointments.filter(date_key=today_key).count(),
        }

        return self.success_response(data=stats)