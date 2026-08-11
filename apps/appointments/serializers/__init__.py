"""
Serializers برای نوبت‌ها — با تاریخ جلالی
"""
from rest_framework import serializers
from apps.appointments.models import Appointment

class AppointmentCreateSerializer(serializers.Serializer):
    """Serializer برای ایجاد نوبت"""
    service_id = serializers.IntegerField()
    jy = serializers.IntegerField()
    jm = serializers.IntegerField()
    jd = serializers.IntegerField()
    time_slot = serializers.CharField(max_length=5)  # HH:MM
    team_member_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_time_slot(self, value):
        import re
        if not re.match(r'^\d{2}:\d{2}$', value):
            raise serializers.ValidationError('فرمت ساعت نامعتبر (HH:MM)')
        try:
            from datetime import datetime
            datetime.strptime(value, '%H:%M')
        except ValueError:
            raise serializers.ValidationError('ساعت نامعتبر')
        return value

    def validate(self, data):
        # بررسی تاریخ جلالی
        jy = data.get('jy')
        jm = data.get('jm')
        jd = data.get('jd')

        if not (1 <= jm <= 12):
            raise serializers.ValidationError('ماه جلالی باید بین ۱ تا ۱۲ باشد')
        if not (1 <= jd <= 31):
            raise serializers.ValidationError('روز جلالی باید بین ۱ تا ۳۱ باشد')

        return data


class AppointmentListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست نوبت‌ها"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.ImageField(source='business.logo', read_only=True)
    team_member_name = serializers.CharField(
        source='team_member.name', read_only=True, default=None
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'jy', 'jm', 'jd', 'date_key', 'time_slot',
            'status', 'status_display',
            'service_name', 'business_name', 'business_logo',
            'team_member_name',
            'total_price', 'deposit_amount', 'remaining_amount',
            'verification_code', 'is_trust_based', 'is_verified',
            'has_review',
            'can_cancel',
            'cancellation_reason', 'cancelled_at',
            'created_at',
        ]

    def get_can_cancel(self, obj):
        return obj.status == Appointment.Status.RESERVED


class AppointmentDetailSerializer(AppointmentListSerializer):
    """Serializer برای جزئیات کامل نوبت"""
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta(AppointmentListSerializer.Meta):
        fields = AppointmentListSerializer.Meta.fields + [
            'customer_phone', 'customer_name',
            'verified_at', 'reminder_sent',
        ]

    def get_customer_name(self, obj):
        return obj.customer.full_name


class CancelAppointmentSerializer(serializers.Serializer):
    """Serializer برای لغو نوبت"""
    reason_text = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        default='',
    )


class VerifyServiceCodeSerializer(serializers.Serializer):
    """Serializer برای تایید کد خدمت"""
    code = serializers.CharField(max_length=4, min_length=4)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('کد باید ۴ رقم باشد')
        return value