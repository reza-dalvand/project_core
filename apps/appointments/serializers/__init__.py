# apps/appointments/serializers/__init__.py

"""
Serializers برای نوبت‌ها — با تاریخ جلالی
+ فیلدهای محاسباتی (فاز ۳)

✅ نسخه مقاوم:
- از source های زنجیره‌ای خطرناک مثل business.city.name استفاده نمی‌کند
- در صورت ناقص بودن داده مرتبط، سرور 500 نمی‌دهد
- خطای serialize شدن هر نوبت لاگ می‌شود
"""

import logging
from datetime import datetime

import jdatetime
from django.utils import timezone
from rest_framework import serializers

from apps.appointments.models import Appointment

logger = logging.getLogger(__name__)


class AppointmentCreateSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    jy = serializers.IntegerField()
    jm = serializers.IntegerField()
    jd = serializers.IntegerField()
    time_slot = serializers.CharField(max_length=5)

    # ✅ فاز ۳: فیلد اعتماد به سالن
    trust_based = serializers.BooleanField(
        required=False,
        default=False,
        help_text='اگر فعال باشد، نوبت بدون کد تایید ثبت می‌شود',
    )

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
            raise serializers.ValidationError('روز جلالی باید بین ۱ تا ۱ باشد')
        return data


class AppointmentListSerializer(serializers.ModelSerializer):
    """Serializer لیست نوبت‌ها + فیلدهای محاسباتی — نسخه مقاوم"""

    service_name = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()
    business_logo = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    # ═══ فیلدهای محاسباتی (فاز ۳) ═══
    hours_left = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    date_key = serializers.SerializerMethodField()
    deposit_paid = serializers.SerializerMethodField()

    trust_based = serializers.BooleanField(
        source='is_trust_based',
        read_only=True,
    )
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

    # ═══════════════════════════════════════════════
    #   Safe getters
    # ═══════════════════════════════════════════════

    def get_service_name(self, obj):
        try:
            return getattr(obj.service, 'name', '') or ''
        except Exception:
            return ''

    def get_business_name(self, obj):
        try:
            return getattr(obj.business, 'name', '') or ''
        except Exception:
            return ''

    def get_business_logo(self, obj):
        try:
            logo = getattr(obj.business, 'logo', None)
            if logo is None:
                return None

            logo_name = getattr(logo, 'name', None)
            if not logo_name:
                return None

            return logo.url
        except Exception:
            return None

    def get_customer_name(self, obj):
        try:
            full_name = getattr(obj.customer, 'full_name', None)
            if full_name:
                return full_name
        except Exception:
            pass

        try:
            return getattr(obj.customer, 'phone', '') or ''
        except Exception:
            return ''

    def get_customer_phone(self, obj):
        try:
            return getattr(obj.customer, 'phone', '') or ''
        except Exception:
            return ''

    def get_employee_name(self, obj):
        """در نسخه بدون تیم، نام کارمند خالی است"""
        return None

    def get_status_display(self, obj):
        try:
            return obj.get_status_display()
        except Exception:
            return getattr(obj, 'status', '') or ''

    def get_date_key(self, obj):
        try:
            date_key = getattr(obj, 'date_key', None)
            if date_key:
                return date_key

            jy = int(getattr(obj, 'jy', 0) or 0)
            jm = int(getattr(obj, 'jm', 0) or 0)
            jd = int(getattr(obj, 'jd', 0) or 0)
            return f"{jy}/{jm:02d}/{jd:02d}"
        except Exception:
            return ''

    def get_hours_left(self, obj):
        """
        محاسبه ساعت مانده تا نوبت
        هماهنگ با فرانت: getHoursUntilAppointment
        """
        try:
            if obj.status != Appointment.Status.RESERVED:
                return 0

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
        try:
            if obj.status != Appointment.Status.RESERVED:
                return False

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
        از آنجا که لغو توسط مشتری غیرفعال شده، همیشه False برمی‌گرداند.
        فقط صاحب کسب‌وکار می‌تواند لغو کند.
        """
        return False

    def get_deposit_paid(self, obj):
        """مبلغ بیعانه پرداخت شده"""
        try:
            return int(getattr(obj, 'deposit_amount', 0) or 0)
        except Exception:
            return 0

    # ═══════════════════════════════════════════════
    #   Fallback برای جلوگیری از 500 هنگام serialize
    # ═══════════════════════════════════════════════

    def to_representation(self, instance):
        try:
            return super().to_representation(instance)
        except Exception as exc:
            logger.exception(
                "Appointment serialization failed: id=%s error=%s",
                getattr(instance, 'id', None),
                exc,
            )
            return self._fallback_representation(instance)

    def _fallback_representation(self, instance):
        def g(attr, default=None):
            try:
                return getattr(instance, attr, default)
            except Exception:
                return default

        try:
            date_key = g('date_key') or ''
            if not date_key:
                jy = int(g('jy', 0) or 0)
                jm = int(g('jm', 0) or 0)
                jd = int(g('jd', 0) or 0)
                date_key = f"{jy}/{jm:02d}/{jd:02d}"
        except Exception:
            date_key = ''

        try:
            status_display = instance.get_status_display()
        except Exception:
            status_display = g('status', '') or ''

        return {
            'id': g('id'),
            'jy': g('jy', 0),
            'jm': g('jm', 0),
            'jd': g('jd', 0),
            'date_key': date_key,
            'time_slot': g('time_slot'),
            'status': g('status', '') or '',
            'status_display': status_display,
            'service_name': self.get_service_name(instance),
            'business_name': self.get_business_name(instance),
            'business_logo': self.get_business_logo(instance),
            'customer_name': self.get_customer_name(instance),
            'customer_phone': self.get_customer_phone(instance),
            'employee_name': None,
            'total_price': g('total_price', 0) or 0,
            'deposit_amount': g('deposit_amount', 0) or 0,
            'deposit_paid': g('deposit_amount', 0) or 0,
            'remaining_amount': g('remaining_amount', 0) or 0,
            'verification_code': g('verification_code', '') or '',
            'trust_based': bool(g('is_trust_based', False)),
            'is_verified': bool(g('is_verified', False)),
            'has_review': bool(g('has_review', False)),
            'hours_left': 0,
            'is_upcoming': False,
            'can_cancel': False,
            'cancellation_reason': g('cancellation_reason', '') or '',
            'cancelled_at': g('cancelled_at'),
            'created_at': g('created_at'),
        }


class AppointmentDetailSerializer(AppointmentListSerializer):
    """
    Serializer جزئیات نوبت — نسخه مقاوم

    ✅ مهم:
    از source زنجیره‌ای مثل business.city.name استفاده نمی‌کند.
    """

    business_address = serializers.SerializerMethodField()
    business_city = serializers.SerializerMethodField()
    service_duration = serializers.SerializerMethodField()

    class Meta(AppointmentListSerializer.Meta):
        fields = AppointmentListSerializer.Meta.fields + [
            'business_address',
            'business_city',
            'service_duration',
            'verified_at',
            'reminder_sent',
        ]

    def get_business_address(self, obj):
        try:
            return getattr(obj.business, 'address', '') or ''
        except Exception:
            return ''

    def get_business_city(self, obj):
        try:
            city = getattr(obj.business, 'city', None)

            if city is None:
                return ''

            # اگر city یک رشته ساده بود
            if isinstance(city, str):
                return city

            # اگر city یک مدل/رابطه بود
            return getattr(city, 'name', '') or ''
        except Exception:
            return ''

    def get_service_duration(self, obj):
        try:
            duration = getattr(obj.service, 'duration', None)
            if duration is None:
                return 0
            return int(duration)
        except Exception:
            return 0

    def _fallback_representation(self, instance):
        data = super()._fallback_representation(instance)

        data.update({
            'business_address': self.get_business_address(instance),
            'business_city': self.get_business_city(instance),
            'service_duration': self.get_service_duration(instance),
            'verified_at': getattr(instance, 'verified_at', None),
            'reminder_sent': bool(getattr(instance, 'reminder_sent', False)),
        })

        return data


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