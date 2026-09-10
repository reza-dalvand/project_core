"""
Serializers برای زمان‌بندی — نسخه نهایی (فاز ۴)
بدون تیم
"""
from rest_framework import serializers
from apps.schedules.models import ServiceSchedule
from apps.services.models import Service


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
    """Serializer زمان‌بندی — نسخه فاز ۴"""

    # ═══ فیلدهای نوشتنی ═══
    # ✅ اصلاح: service به عنوان PrimaryKeyRelatedField با queryset
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        required=True,
        help_text='شناسه خدمت (عدد)',
    )

    breaks = ScheduleBreakSerializer(many=True, required=False, default=list)

    # ═══ فیلدهای خواندنی ═══
    # ✅ اصلاح: business فقط خواندنی — فرانت نمی‌فرستد
    business = serializers.PrimaryKeyRelatedField(read_only=True)
    service_id = serializers.IntegerField(source='service.id', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    date_key = serializers.CharField(read_only=True)
    slot_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ServiceSchedule
        fields = [
            'id', 'business', 'service', 'service_id',
            'jy', 'jm', 'jd', 'date_key',
            'work_start', 'work_end', 'slot_duration',
            'breaks', 'slot_count',
            'service_name', 'business_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'business', 'service_id', 'date_key',
            'slot_count', 'service_name', 'business_name',
            'created_at', 'updated_at',
        ]
        # ✅ اصلاح: فیلدهای لازم برای ایجاد
        extra_kwargs = {
            'jy': {'required': True},
            'jm': {'required': True},
            'jd': {'required': True},
            'work_start': {'required': True},
            'work_end': {'required': True},
            'slot_duration': {'required': True},
        }

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

        # ✅ بررسی تداخل با schedule قبلی
        service = data.get('service')
        if service and self.instance is None:
            date_key = f'{jy}/{jm:02d}/{jd:02d}'
            exists = ServiceSchedule.objects.filter(
                service=service,
                date_key=date_key,
            ).exists()
            if exists:
                raise serializers.ValidationError(
                    'برای این خدمت در این تاریخ قبلاً زمان‌بندی ثبت شده است'
                )

        return data

    def validate_slot_duration(self, value):
        if value < 15:
            raise serializers.ValidationError(
                'مدت هر نوبت باید حداقل ۱۵ دقیقه باشد'
            )
        if value > 360:
            raise serializers.ValidationError(
                'مدت هر نوبت نمی‌تواند بیشتر از ۶ ساعت باشد'
            )
        return value

    def create(self, validated_data):
        """
        ✅ اصلاح: کسب‌وکار از کاربر لاگین‌شده گرفته می‌شود
        فرانت نیازی به ارسال business ندارد
        """
        request = self.context.get('request')
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            raise serializers.ValidationError(
                'شما کسب‌وکار تأییدشده‌ای ندارید. '
                'ابتدا کسب‌وکار خود را ثبت و تأیید کنید.'
            )

        validated_data['business'] = business
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        ✅ اصلاح: مالکیت کسب‌وکار بررسی می‌شود
        """
        request = self.context.get('request')
        if instance.business.owner != request.user:
            raise serializers.ValidationError(
                'شما اجازه ویرایش این زمان‌بندی را ندارید'
            )
        return super().update(instance, validated_data)


class ServiceScheduleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceSchedule
        fields = ['service', 'jy', 'jm', 'jd', 'work_start', 'work_end', 'slot_duration', 'breaks']

    def create(self, validated_data):
        request = self.context.get('request')
        # دریافت کسب‌وکار کاربر
        business = request.user.businesses.filter(is_active=True, status='approved').first()
        if not business:
            raise serializers.ValidationError("کسب‌وکار تایید شده یافت نشد")
        
        validated_data['business'] = business
        
        # تولید date_key
        jy = validated_data['jy']
        jm = validated_data['jm']
        jd = validated_data['jd']
        date_key = f"{jy}/{jm:02d}/{jd:02d}"
        validated_data['date_key'] = date_key
        
        # ✅ استفاده از update_or_create به جای create
        # این کار از IntegrityError جلوگیری می‌کند و اگر رکورد تکراری بود، آن را آپدیت می‌کند
        schedule, created = ServiceSchedule.objects.update_or_create(
            service=validated_data['service'],
            date_key=date_key,
            defaults={
                'business': business,
                'jy': jy,
                'jm': jm,
                'jd': jd,
                'work_start': validated_data['work_start'],
                'work_end': validated_data['work_end'],
                'slot_duration': validated_data['slot_duration'],
                'breaks': validated_data.get('breaks', []),
            }
        )
        return schedule


class ServiceScheduleUpdateSerializer(ServiceScheduleSerializer):
    """Serializer بروزرسانی زمان‌بندی"""

    # در بروزرسانی، همه فیلدها اختیاری هستند
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        required=False,
    )
    jy = serializers.IntegerField(required=False)
    jm = serializers.IntegerField(required=False)
    jd = serializers.IntegerField(required=False)
    work_start = serializers.TimeField(required=False)
    work_end = serializers.TimeField(required=False)
    slot_duration = serializers.IntegerField(required=False)

    class Meta(ServiceScheduleSerializer.Meta):
        extra_kwargs = {}  # ✅ override: هیچ فیلد لازمی در بروزرسانی نیست

    def validate(self, data):
        """در بروزرسانی، مقادیر فعلی را با مقادیر جدید ترکیب کن"""
        instance = self.instance

        jy = data.get('jy', instance.jy)
        jm = data.get('jm', instance.jm)
        jd = data.get('jd', instance.jd)

        if not (1 <= jm <= 12):
            raise serializers.ValidationError('ماه جلالی باید بین ۱ تا ۱۲ باشد')

        if not (1 <= jd <= 31):
            raise serializers.ValidationError('روز جلالی باید بین ۱ تا ۳۱ باشد')

        work_start = data.get('work_start', instance.work_start)
        work_end = data.get('work_end', instance.work_end)

        if work_end <= work_start:
            raise serializers.ValidationError(
                'ساعت پایان باید بعد از ساعت شروع باشد'
            )

        return data


class WeeklyScheduleQuerySerializer(serializers.Serializer):
    service_id = serializers.IntegerField(required=True)
    days_ahead = serializers.IntegerField(
        required=False, default=30, min_value=1, max_value=60
    )