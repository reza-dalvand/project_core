"""
Views برای مدیریت نوبت‌ها — با تاریخ جلالی
"""
import logging
import jdatetime
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q
from django.utils import timezone

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
                is_trust_based=serializer.validated_data.get('trust_based', False),
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
            OpenApiParameter(name='status', type=str, required=False, enum=['all', 'reserved', 'cancelled', 'done']),
            OpenApiParameter(name='search', type=str, required=False),
            OpenApiParameter(name='date_filter', type=str, required=False, enum=['today', 'week', 'month', 'all']),
            OpenApiParameter(name='date_from', type=str, required=False),
            OpenApiParameter(name='date_to', type=str, required=False),
        ],
        tags=['Appointments - Business'],
        summary='نوبت‌های کسب‌وکار من',
    )
    def get_queryset(self):
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

        # ─── فیلتر بازه زمانی ───
        date_filter = self.request.query_params.get('date_filter')
        if date_filter:
            today = jdatetime.date.today()
            today_key = f'{today.year}/{today.month:02d}/{today.day:02d}'

            if date_filter == 'today':
                qs = qs.filter(date_key=today_key)

            elif date_filter == 'week':
                week_end = today + jdatetime.timedelta(days=7)
                week_end_key = f'{week_end.year}/{week_end.month:02d}/{week_end.day:02d}'
                qs = qs.filter(date_key__gte=today_key, date_key__lte=week_end_key)

            elif date_filter == 'month':
                # ✅ اصلاح شده: استفاده از تابع دقیق طول ماه جلالی
                month_start_key = f'{today.year}/{today.month:02d}/01'
                month_end_day = jdatetime.jalaali_month_length(today.year, today.month)
                month_end_key = f'{today.year}/{today.month:02d}/{month_end_day:02d}'
                qs = qs.filter(date_key__gte=month_start_key, date_key__lte=month_end_key)

        # ─── فیلتر بازه دلخواه ───
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
        qs = Appointment.objects.select_related('service', 'business', 'customer')

        if user.is_authenticated:
            user_business = user.businesses.filter(is_active=True).first()
            if user_business:
                return qs.filter(Q(customer=user) | Q(business=user_business))
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
            appointment = Appointment.objects.get(id=pk, customer=request.user)
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
        business = request.user.businesses.filter(is_active=True, status='approved').first()

        try:
            appointment = Appointment.objects.get(id=pk, business=business)
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CancelAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            appointment.cancel_by_salon(reason=serializer.validated_data.get('reason_text', ''))
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
        business = request.user.businesses.filter(is_active=True, status='approved').first()

        try:
            appointment = Appointment.objects.get(id=pk, business=business)
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VerifyServiceCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entered_code = serializer.validated_data['code']

        try:
            # ✅ هندل کردن نوبت‌های اعتمادی (Trust-Based)
            # در نوبت‌های اعتمادی کد تولید نمی‌شود (خالی است) و فرانت ممکن است 0000 بفرستد
            if appointment.is_trust_based:
                # برای نوبت اعتمادی، کد را مستقیماً روی همان مقدار پیش‌فرض یا 0000 ست می‌کنیم تا BookingService ارور ندهد
                code_to_verify = appointment.verification_code or '0000'
                success = BookingService.verify_service_code(
                    appointment=appointment,
                    entered_code=code_to_verify,
                    verified_by=request.user,
                )
            else:
                success = BookingService.verify_service_code(
                    appointment=appointment,
                    entered_code=entered_code,
                    verified_by=request.user,
                )

            if success:
                return self.success_response(
                    data={
                        'appointment_id': appointment.id,
                        'status': appointment.status,
                        'verified_at': appointment.verified_at,
                    },
                    # ✅ پیام جدید و دقیق درخواستی
                    message='خدمت با موفقیت انجام شد و بیعانه آزاد شد.',
                )
            else:
                return self.error_response(
                    message='کد وارد شده صحیح نیست',
                    code='INVALID_CODE',
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except BookingException as e:
            return e.as_response()
        except Exception as e:
            logger.exception(f"Verify code error: {e}")
            return self.error_response(
                message='خطا در تایید کد خدمت',
                code='VERIFY_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RegenerateCodeView(APIView, StandardResponseMixin):
    """تولید مجدد کد تایید"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Appointments - Customer'],
        summary='تولید مجدد کد تایید',
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(id=pk, customer=request.user)
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        # جلوگیری از تولید کد برای نوبت‌های اعتمادی
        if appointment.is_trust_based:
            return self.error_response(
                message='این نوبت بر اساس اعتماد است و نیازی به کد تایید ندارد.',
                code='TRUST_BASED_APPOINTMENT',
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_code = BookingService.regenerate_verification_code(appointment)
            return self.success_response(
                data={'verification_code': new_code},
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

        business = request.user.businesses.filter(is_active=True, status='approved').first()

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
    

# ═══════ در انتهای فایل، قبل از آخرین کلاس یا بعد از آن اضافه شود ═══════

class BusinessTodayAppointmentsView(generics.ListAPIView, StandardResponseMixin):
    """
    نوبت‌های فعال امروز کسب‌وکار
    فقط نوبت‌های با وضعیت reserved برای تاریخ امروز
    برای ویجت داشبورد مدیریت
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    serializer_class = AppointmentListSerializer

    @extend_schema(
        tags=['Appointments - Business'],
        summary='نوبت‌های فعال امروز',
        description='نوبت‌های رزرو شده امروز برای نمایش در داشبورد مدیریت',
    )
    def get_queryset(self):
        import jdatetime

        business = self.request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        today = jdatetime.date.today()
        today_key = f'{today.year}/{today.month:02d}/{today.day:02d}'

        return Appointment.objects.filter(
            business=business,
            status=Appointment.Status.RESERVED,
            date_key=today_key,
        ).select_related(
            'service', 'customer'
        ).order_by('time_slot')