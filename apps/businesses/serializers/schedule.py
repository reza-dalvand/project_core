"""
Serializers برای مدیریت زمان‌بندی
"""
from rest_framework import serializers
from apps.businesses.models import Schedule, ScheduleBreak, Service
import datetime


class ScheduleBreakSerializer(serializers.ModelSerializer):
    """Serializer برای بازه‌های استراحت"""

    class Meta:
        model = ScheduleBreak
        fields = ['id', 'start_time', 'end_time']

    def validate(self, data):
        """اعتبارسنجی بازه استراحت"""
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError(
                    'زمان پایان استراحت باید بعد از زمان شروع باشد'
                )

        return data


class ScheduleListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست زمان‌بندی‌ها"""
    breaks = ScheduleBreakSerializer(many=True, read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = Schedule
        fields = [
            'id', 'weekday', 'weekday_display',
            'is_working', 'start_time', 'end_time',
            'slot_duration',
            'breaks',
            'service_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ScheduleDetailSerializer(serializers.ModelSerializer):
    """Serializer کامل برای جزئیات زمان‌بندی"""
    breaks = ScheduleBreakSerializer(many=True, read_only=True)
    break_data = ScheduleBreakSerializer(many=True, write_only=True, required=False)
    service_name = serializers.CharField(source='service.name', read_only=True)
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)
    available_slots_count = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [
            'id', 'weekday', 'weekday_display',
            'is_working', 'start_time', 'end_time',
            'slot_duration',
            'breaks', 'break_data',
            'service_name', 'available_slots_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_available_slots_count(self, obj):
        """محاسبه تعداد slot های قابل رزرو"""
        if not obj.is_working or not obj.start_time or not obj.end_time:
            return 0

        # تبدیل time به دقیقه
        start_minutes = obj.start_time.hour * 60 + obj.start_time.minute
        end_minutes = obj.end_time.hour * 60 + obj.end_time.minute

        total_minutes = end_minutes - start_minutes

        # کسر زمان استراحت‌ها
        for break_time in obj.breaks.all():
            break_start = break_time.start_time.hour * 60 + break_time.start_time.minute
            break_end = break_time.end_time.hour * 60 + break_time.end_time.minute
            total_minutes -= (break_end - break_start)

        return max(0, total_minutes // obj.slot_duration)

    def validate(self, data):
        """اعتبارسنجی کلی"""
        is_working = data.get('is_working', getattr(self.instance, 'is_working', True))

        if is_working:
            start_time = data.get('start_time', getattr(self.instance, 'start_time', None))
            end_time = data.get('end_time', getattr(self.instance, 'end_time', None))

            if not start_time or not end_time:
                raise serializers.ValidationError(
                    'برای روز کاری، ساعت شروع و پایان الزامی است'
                )

            if end_time <= start_time:
                raise serializers.ValidationError(
                    'ساعت پایان باید بعد از ساعت شروع باشد'
                )

        return data

    def validate_slot_duration(self, value):
        """اعتبارسنجی مدت هر slot"""
        if value < 15:
            raise serializers.ValidationError('مدت هر نوبت باید حداقل ۱۵ دقیقه باشد')
        if value > 120:
            raise serializers.ValidationError('مدت هر نوبت نمی‌تواند بیشتر از ۲ ساعت باشد')
        return value


class ScheduleCreateUpdateSerializer(ScheduleDetailSerializer):
    """Serializer برای ایجاد/بروزرسانی زمان‌بندی"""
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='service',
        write_only=True
    )

    def validate_service_id(self, value):
        """اعتبارسنجی خدمت - فقط خدمات همان کسب‌وکار"""
        request = self.context.get('request')
        business = request.user.business

        if value.business != business:
            raise serializers.ValidationError('این خدمت متعلق به کسب‌وکار شما نیست')

        return value

    def create(self, validated_data):
        """ایجاد زمان‌بندی جدید"""
        request = self.context.get('request')
        break_data = validated_data.pop('break_data', [])
        validated_data['business'] = request.user.business

        schedule = Schedule.objects.create(**validated_data)

        # ایجاد بازه‌های استراحت
        for break_item in break_data:
            ScheduleBreak.objects.create(schedule=schedule, **break_item)

        return schedule

    def update(self, instance, validated_data):
        """بروزرسانی زمان‌بندی"""
        request = self.context.get('request')
        if instance.business.owner != request.user:
            raise serializers.ValidationError('شما اجازه ویرایش این زمان‌بندی را ندارید')

        break_data = validated_data.pop('break_data', None)

        # بروزرسانی فیلدها
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # بروزرسانی بازه‌های استراحت
        if break_data is not None:
            # حذف بازه‌های قبلی
            instance.breaks.all().delete()

            # ایجاد بازه‌های جدید
            for break_item in break_data:
                ScheduleBreak.objects.create(schedule=instance, **break_item)

        return instance


class WeeklyScheduleSerializer(serializers.Serializer):
    """Serializer برای دریافت/ذخیره زمان‌بندی هفتگی"""
    service_id = serializers.IntegerField()
    schedules = ScheduleCreateUpdateSerializer(many=True)

    def validate(self, data):
        """اعتبارسنجی - حداکثر ۷ روز"""
        schedules = data.get('schedules', [])
        if len(schedules) > 7:
            raise serializers.ValidationError(
                'حداکثر ۷ روز در هفته می‌توانید تنظیم کنید'
            )

        # بررسی تکراری نبودن روزها
        weekdays = [s.get('weekday') for s in schedules]
        if len(weekdays) != len(set(weekdays)):
            raise serializers.ValidationError(
                'هر روز هفته فقط یکبار می‌تواند تنظیم شود'
            )

        return data