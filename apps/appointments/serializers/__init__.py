"""
Serializers برای نوبت‌ها — با تاریخ جلالی
+ فیلدهای محاسباتی (فاز ۳)
"""
from rest_framework import serializers
from apps.appointments.models import Appointment
import jdatetime
from datetime import datetime
from django.utils import timezone


class AppointmentCreateSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    jy = serializers.IntegerField()
    jm = serializers.IntegerField()
    jd = serializers.IntegerField()
    time_slot = serializers.CharField(max_length=5)

    def validate_time_slot(self, value):
        import re
        if not re.match(r'^\d{2}:\d{2}$', value):
            raise serializers.ValidationError('فرمت ساعت نامعتبر (HH:MM)')
        try:
            datetime.strptime(value, '%H:%M')
        except ValueError:
            raise serializers.ValidationError('ساعت نامعتبر')
        return value

    def validate(self, data):
        jy = data.get('jy')
        jm = data.get('jm')
        jd = data.get('jd')
        if not (1 <= jm <= 12):
            raise serializers.ValidationError('ماه جلالی باید بین ۱ تا ۱۲ باشد')
        if not (1 <= jd <= 31):
            raise serializers.ValidationError('روز جلالی باید بین ۱ تا ۳۱ باشد')
        return data


class AppointmentListSerializer(serializers.ModelSerializer):
    """Serializer لیست نوبت‌ها + فیلدهای محاسباتی"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.ImageField(source='business.logo', read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    employee_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # ═══ فیلدهای محاسباتی (فاز ۳) ═══
    hours_left = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    date_key = serializers.CharField(read_only=True)
    deposit_paid = serializers.SerializerMethodField()
    trust_based = serializers.BooleanField(source='is_trust_based', read_only=True)
    verification_code = serializers.CharField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'jy', 'jm', 'jd', 'date_key', 'time_slot',
            'status', 'status_display',
            'service_name', 'business_name', 'business_logo',
            'customer_name', 'customer_phone', 'employee_name',
            'total_price', 'deposit_amount', 'deposit_paid',
            'remaining_amount',
            'verification_code', 'trust_based', 'is_verified',
            'has_review',
            # ═══ فیلدهای محاسباتی ═══
            'hours_left', 'is_upcoming', 'can_cancel',
            'cancellation_reason', 'cancelled_at',
            'created_at',
        ]

    def get_customer_name(self, obj):
        return obj.customer.full_name

    def get_employee_name(self, obj):
        """در نسخه بدون تیم، نام کارمند خالی است"""
        return None

    def get_hours_left(self, obj):
        """
        محاسبه ساعت مانده تا نوبت
        هماهنگ با فرانت: getHoursUntilAppointment
        """
        if obj.status != Appointment.Status.RESERVED:
            return 0
        try:
            gregorian_date = jdatetime.date(
                obj.jy, obj.jm, obj.jd
            ).togregorian()
            apt_datetime = datetime.combine(
                gregorian_date, obj.time_slot
            )
            apt_datetime = timezone.make_aware(apt_datetime)
            now = timezone.now()
            diff = (apt_datetime - now).total_seconds() / 3600
            return round(max(0, diff), 1)
        except Exception:
            return 0

    def get_is_upcoming(self, obj):
        """
        آیا نوبت آینده است؟
        هماهنگ با فرانت: appointment.isUpcoming
        """
        if obj.status != Appointment.Status.RESERVED:
            return False
        try:
            gregorian_date = jdatetime.date(
                obj.jy, obj.jm, obj.jd
            ).togregorian()
            apt_datetime = datetime.combine(
                gregorian_date, obj.time_slot
            )
            apt_datetime = timezone.make_aware(apt_datetime)
            return apt_datetime > timezone.now()
        except Exception:
            return False

    def get_can_cancel(self, obj):
        """
        آیا نوبت قابل لغو است؟
        هماهنگ با فرانت: canCancelAppointment
        قانون: فقط اگر ۱۲ ساعت یا بیشتر مانده باشد
        """
        if obj.status != Appointment.Status.RESERVED:
            return False
        hours_left = self.get_hours_left(obj)
        CANCELLATION_THRESHOLD_HOURS = 12
        return hours_left >= CANCELLATION_THRESHOLD_HOURS

    def get_deposit_paid(self, obj):
        """مبلغ بیعانه پرداخت شده"""
        return obj.deposit_amount


class AppointmentDetailSerializer(AppointmentListSerializer):
    """Serializer جزئیات نوبت"""
    business_address = serializers.CharField(
        source='business.address', read_only=True
    )
    business_city = serializers.CharField(
        source='business.city.name', read_only=True
    )
    service_duration = serializers.IntegerField(
        source='service.duration', read_only=True
    )

    class Meta(AppointmentListSerializer.Meta):
        fields = AppointmentListSerializer.Meta.fields + [
            'business_address', 'business_city',
            'service_duration',
            'verified_at', 'reminder_sent',
        ]


class CancelAppointmentSerializer(serializers.Serializer):
    reason_text = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        default='',
    )


class VerifyServiceCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=4, min_length=4)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('کد باید ۴ رقم باشد')
        return value