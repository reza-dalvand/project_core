"""
Serializers برای زمان‌بندی — با تاریخ جلالی
بدون تیم
"""
from rest_framework import serializers
from apps.schedules.models import ServiceSchedule


class ScheduleBreakSerializer(serializers.Serializer):
    start = serializers.TimeField()
    end = serializers.TimeField()

    def validate(self, data):
        if data['end'] <= data['start']:
            raise serializers.ValidationError(
                'زمان پایان استراحت باید بعد از زمان شروع باشد'
            )
        return data


class ServiceScheduleSerializer(serializers.ModelSerializer):
    breaks = ScheduleBreakSerializer(many=True, required=False, default=list)
    service_name = serializers.CharField(source='service.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    # ❌ team_member_name حذف شد

    class Meta:
        model = ServiceSchedule
        fields = [
            'id', 'business', 'service',
            # ❌ team_member حذف شد
            'jy', 'jm', 'jd', 'date_key',
            'work_start', 'work_end', 'slot_duration',
            'breaks', 'slot_count',
            'service_name', 'business_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['date_key', 'slot_count', 'created_at', 'updated_at']

    def validate(self, data):
        jy = data.get('jy')
        jm = data.get('jm')
        jd = data.get('jd')
        if not all([jy, jm, jd]):
            raise serializers.ValidationError('تاریخ جلالی الزامی است')
        if not (1 <= jm <= 12):
            raise serializers.ValidationError('ماه جلالی باید بین ۱ تا ۱۲ باشد')
        if not (1 <= jd <= 31):
            raise serializers.ValidationError('روز جلالی باید بین ۱ تا ۳۱ باشد')
        work_start = data.get('work_start')
        work_end = data.get('work_end')
        if work_start and work_end and work_end <= work_start:
            raise serializers.ValidationError(
                'ساعت پایان باید بعد از ساعت شروع باشد'
            )
        return data

    def validate_slot_duration(self, value):
        if value < 15:
            raise serializers.ValidationError('مدت هر نوبت باید حداقل ۱۵ دقیقه باشد')
        if value > 120:
            raise serializers.ValidationError('مدت هر نوبت نمی‌تواند بیشتر از ۲ ساعت باشد')
        return value


class ServiceScheduleCreateSerializer(ServiceScheduleSerializer):
    def create(self, validated_data):
        request = self.context.get('request')
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        validated_data['business'] = business
        return super().create(validated_data)


class ServiceScheduleUpdateSerializer(ServiceScheduleSerializer):
    def update(self, instance, validated_data):
        request = self.context.get('request')
        if instance.business.owner != request.user:
            raise serializers.ValidationError('شما اجازه ویرایش این زمان‌بندی را ندارید')
        return super().update(instance, validated_data)


class WeeklyScheduleQuerySerializer(serializers.Serializer):
    service_id = serializers.IntegerField(required=True)
    days_ahead = serializers.IntegerField(required=False, default=30, min_value=1, max_value=60)