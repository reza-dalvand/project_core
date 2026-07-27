"""
Serializers برای مدیریت کارمندان
"""
from rest_framework import serializers
from apps.businesses.models import Employee, Service
from apps.core.validators import validate_iranian_phone


class ServiceBriefSerializer(serializers.ModelSerializer):
    """Serializer خلاصه برای خدمات"""

    class Meta:
        model = Service
        fields = ['id', 'name', 'final_price', 'duration_minutes']


class EmployeeListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست کارمندان"""
    services = ServiceBriefSerializer(many=True, read_only=True)
    services_count = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'phone', 'avatar',
            'role', 'experience', 'bio',
            'is_active', 'order',
            'services', 'services_count',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def get_services_count(self, obj):
        """تعداد خدمات فعال کارمند"""
        return obj.services.filter(is_active=True).count()


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """Serializer کامل برای جزئیات کارمند"""
    services = ServiceBriefSerializer(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='services',
        many=True,
        write_only=True,
        required=False
    )
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'phone', 'avatar',
            'role', 'experience', 'bio',
            'is_active', 'order',
            'services', 'service_ids',
            'business_name',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def validate_phone(self, value):
        """اعتبارسنجی شماره تماس"""
        if value:
            try:
                return validate_iranian_phone(value)
            except Exception as e:
                raise serializers.ValidationError(str(e))
        return value

    def validate_name(self, value):
        """اعتبارسنجی نام"""
        if not value or not value.strip():
            raise serializers.ValidationError('نام کارمند الزامی است')
        if len(value.strip()) < 3:
            raise serializers.ValidationError('نام باید حداقل ۳ کاراکتر باشد')
        return value.strip()

    def validate_service_ids(self, value):
        """اعتبارسنجی خدمات - فقط خدمات همان کسب‌وکار"""
        request = self.context.get('request')
        business = request.user.business

        for service in value:
            if service.business != business:
                raise serializers.ValidationError(
                    f'خدمت {service.name} متعلق به این کسب‌وکار نیست'
                )

        return value


class EmployeeCreateSerializer(EmployeeDetailSerializer):
    """Serializer برای ایجاد کارمند جدید"""

    def create(self, validated_data):
        """ایجاد کارمند جدید"""
        request = self.context.get('request')
        services = validated_data.pop('services', [])
        validated_data['business'] = request.user.business

        employee = Employee.objects.create(**validated_data)
        if services:
            employee.services.set(services)

        return employee


class EmployeeUpdateSerializer(EmployeeDetailSerializer):
    """Serializer برای بروزرسانی کارمند"""

    def update(self, instance, validated_data):
        """بروزرسانی کارمند"""
        request = self.context.get('request')
        if instance.business.owner != request.user:
            raise serializers.ValidationError('شما اجازه ویرایش این کارمند را ندارید')

        services = validated_data.pop('services', None)

        # بروزرسانی فیلدها
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # بروزرسانی خدمات
        if services is not None:
            instance.services.set(services)

        return instance