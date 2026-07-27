"""
Serializers برای اسلات‌های زمانی
"""
from rest_framework import serializers


class AvailableDateSerializer(serializers.Serializer):
    """Serializer برای روزهای دارای اسلات آزاد"""
    jy = serializers.IntegerField()
    jm = serializers.IntegerField()
    jd = serializers.IntegerField()
    day_of_week = serializers.IntegerField()
    weekday_name = serializers.CharField()
    date = serializers.DateField()
    available_slots_count = serializers.IntegerField()
    is_today = serializers.BooleanField()
    is_friday = serializers.BooleanField()


class AvailableSlotSerializer(serializers.Serializer):
    """Serializer برای یک اسلات زمانی"""
    id = serializers.CharField()
    date = serializers.DateField()
    start_time = serializers.CharField()
    end_time = serializers.CharField()
    is_available = serializers.BooleanField()
    display_time = serializers.CharField()


class SlotQuerySerializer(serializers.Serializer):
    """Serializer برای پارامترهای کوئری دریافت اسلات"""
    service_id = serializers.IntegerField(required=True)
    date = serializers.DateField(required=True)
    employee_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_service_id(self, value):
        from apps.businesses.models import Service
        if not Service.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('خدمت مورد نظر یافت نشد')
        return value

    def validate_employee_id(self, value):
        if value:
            from apps.businesses.models import Employee
            if not Employee.objects.filter(id=value, is_active=True).exists():
                raise serializers.ValidationError('کارمند مورد نظر یافت نشد')
        return value


class DateQuerySerializer(serializers.Serializer):
    """Serializer برای پارامترهای کوئری دریافت روزهای آزاد"""
    service_id = serializers.IntegerField(required=True)
    days_ahead = serializers.IntegerField(required=False, default=30, min_value=1, max_value=60)