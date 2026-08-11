"""
Serializers برای خدمات
"""
from rest_framework import serializers
from .models import Service


class ServiceListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست خدمات"""
    final_price = serializers.ReadOnlyField()
    discount_amount = serializers.ReadOnlyField()
    app_fee = serializers.ReadOnlyField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    sub_service_name = serializers.CharField(source='sub_service.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description',
            'original_price', 'discount_percent',
            'final_price', 'discount_amount', 'app_fee',
            'has_deposit', 'deposit_amount',
            'duration', 'renewal_days',
            'is_active',
            'category_name', 'sub_service_name',
            'business_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ServiceDetailSerializer(ServiceListSerializer):
    """Serializer کامل برای جزئیات خدمت"""

    class Meta(ServiceListSerializer.Meta):
        fields = ServiceListSerializer.Meta.fields + [
            'category', 'sub_service', 'business',
        ]


class ServiceCreateSerializer(serializers.ModelSerializer):
    """Serializer برای ایجاد خدمت جدید"""
    category = serializers.IntegerField(write_only=True)
    sub_service = serializers.IntegerField(write_only=True)

    class Meta:
        model = Service
        fields = [
            'name', 'category', 'sub_service', 'description',
            'original_price', 'discount_percent',
            'has_deposit', 'deposit_amount',
            'duration', 'renewal_days', 'is_active',
        ]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('نام خدمت الزامی است')
        if len(value.strip()) < 3:
            raise serializers.ValidationError('نام خدمت باید حداقل ۳ کاراکتر باشد')
        return value.strip()

    def validate_original_price(self, value):
        if value < 0:
            raise serializers.ValidationError('قیمت نمی‌تواند منفی باشد')
        return value

    def validate_discount_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError('درصد تخفیف باید بین ۰ تا ۱۰۰ باشد')
        return value

    def validate(self, data):
        # بررسی بیعانه
        original_price = data.get('original_price', 0)
        discount_percent = data.get('discount_percent', 0)
        deposit_amount = data.get('deposit_amount', 0)

        if original_price and discount_percent is not None:
            discount_amount = int(original_price * discount_percent / 100)
            final_price = max(0, original_price - discount_amount)

            if data.get('has_deposit', False) and deposit_amount > final_price:
                raise serializers.ValidationError({
                    'deposit_amount': 'مبلغ بیعانه نمی‌تواند بیشتر از قیمت نهایی باشد'
                })

        # بررسی category و sub_service
        from apps.categories.models import ServiceCategory, SubService

        category_id = data.get('category')
        sub_service_id = data.get('sub_service')

        try:
            category = ServiceCategory.objects.get(id=category_id)
            data['category'] = category
        except ServiceCategory.DoesNotExist:
            raise serializers.ValidationError({'category': 'دسته‌بندی یافت نشد'})

        try:
            sub_service = SubService.objects.get(id=sub_service_id)
            data['sub_service'] = sub_service
        except SubService.DoesNotExist:
            raise serializers.ValidationError({'sub_service': 'زیرخدمت یافت نشد'})

        return data


class ServiceUpdateSerializer(ServiceCreateSerializer):
    """Serializer برای بروزرسانی خدمت"""

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if instance.business.owner != request.user:
            raise serializers.ValidationError('شما اجازه ویرایش این خدمت را ندارید')
        return super().update(instance, validated_data)