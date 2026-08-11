"""
Serializers برای نوبت‌ها
"""
from rest_framework import serializers
from apps.bookings.models import Appointment, CancellationRequest
from apps.businesses.serializers.business import ServiceBriefSerializer
from apps.accounts.serializers.auth import UserProfileSerializer


class AppointmentCreateSerializer(serializers.Serializer):
    """Serializer برای ایجاد نوبت"""
    service_id = serializers.IntegerField()
    date = serializers.DateField()
    time = serializers.CharField(max_length=5)  # HH:MM
    employee_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_service_id(self, value):
        from apps.businesses.models import Service
        try:
            service = Service.objects.select_related('business').get(
                id=value, is_active=True
            )
        except Service.DoesNotExist:
            raise serializers.ValidationError('خدمت مورد نظر یافت نشد')

        if service.business.status != 'approved':
            raise serializers.ValidationError('این کسب‌وکار هنوز تایید نشده است')

        return value

    def validate_time(self, value):
        import re
        if not re.match(r'^\d{2}:\d{2}$', value):
            raise serializers.ValidationError('فرمت ساعت نامعتبر (HH:MM)')

        try:
            from datetime import datetime
            datetime.strptime(value, '%H:%M')
        except ValueError:
            raise serializers.ValidationError('ساعت نامعتبر')

        return value

    def validate_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError('تاریخ نمی‌تواند در گذشته باشد')
        return value

    def validate(self, data):
        # بررسی تکراری نبودن نوبت
        request = self.context.get('request')
        if request:
            existing = Appointment.objects.filter(
                customer=request.user,
                date=data['date'],
                time=data['time'],
                status__in=[Appointment.Status.RESERVED, Appointment.Status.CONFIRMED],
            ).exists()
            if existing:
                raise serializers.ValidationError(
                    'شما در این تاریخ و ساعت نوبت دیگری دارید'
                )
        return data


class AppointmentListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست نوبت‌ها"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.ImageField(source='business.logo', read_only=True)
    employee_name = serializers.CharField(source='employee.name', read_only=True, default=None)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    date_display = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_regenerate_code = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'date', 'time', 'status', 'status_display',
            'service_name', 'business_name', 'business_logo',
            'employee_name', 'original_price', 'discount_percent',
            'final_price', 'deposit_amount', 'deposit_paid',
            'verification_code', 'date_display',
            'can_cancel', 'can_regenerate_code',
            'cancellation_reason', 'created_at',
        ]

    def get_date_display(self, obj):
        import jdatetime
        j_date = jdatetime.date.fromgregorian(date=obj.date)
        # لیست ماه‌های فارسی
        jalali_months = [
            'فروردین', 'اردیبهشت', 'خرداد',
            'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر',
            'دی', 'بهمن', 'اسفند'
        ]
        month_name = jalali_months[j_date.month - 1]
        return f"{j_date.day} {month_name} {j_date.year}"

    def get_can_cancel(self, obj):
        if obj.status not in [Appointment.Status.RESERVED, Appointment.Status.CONFIRMED]:
            return False

        from datetime import datetime
        from django.utils import timezone

        apt_dt = datetime.combine(obj.date, obj.time)
        apt_dt = timezone.make_aware(apt_dt)
        now = timezone.now()

        return (apt_dt - now).total_seconds() > 0

    def get_can_regenerate_code(self, obj):
        if obj.status not in [Appointment.Status.RESERVED, Appointment.Status.CONFIRMED]:
            return False

        if not obj.code_generated_at:
            return True

        from django.utils import timezone
        elapsed = timezone.now() - obj.code_generated_at
        return elapsed.total_seconds() >= 300  # ۵ دقیقه


class AppointmentDetailSerializer(AppointmentListSerializer):
    """Serializer برای جزئیات کامل نوبت"""
    service = ServiceBriefSerializer(read_only=True)
    customer = UserProfileSerializer(read_only=True)

    class Meta(AppointmentListSerializer.Meta):
        fields = AppointmentListSerializer.Meta.fields + [
            'service', 'customer', 'verified_at', 'cancelled_at',
            'code_generated_at',
        ]


class CancelBookingSerializer(serializers.Serializer):
    """Serializer برای لغو نوبت"""
    reason_text = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        default='',
    )


class CancelByBusinessSerializer(serializers.Serializer):
    """Serializer برای لغو نوبت توسط کسب‌وکار"""
    reason_text = serializers.CharField(
        required=True,
        max_length=500,
    )
    reason_type = serializers.ChoiceField(
        choices=CancellationRequest.Reason.choices,
        default=CancellationRequest.Reason.SALON_CLOSED,
    )


class VerifyServiceCodeSerializer(serializers.Serializer):
    """Serializer برای تایید کد خدمت"""
    code = serializers.CharField(max_length=4, min_length=4)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('کد باید ۴ رقم باشد')
        return value


class RegenerateCodeSerializer(serializers.Serializer):
    """Serializer برای تولید مجدد کد تایید"""
    pass


class CancellationRequestSerializer(serializers.ModelSerializer):
    """Serializer برای درخواست‌های لغو"""
    reason_type_display = serializers.CharField(
        source='get_reason_type_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = CancellationRequest
        fields = [
            'id', 'reason_type', 'reason_type_display',
            'reason_text', 'status', 'status_display',
            'refund_amount', 'penalty_amount',
            'created_at', 'reviewed_at',
        ]