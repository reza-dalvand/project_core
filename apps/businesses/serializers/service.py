"""
Serializers برای مدیریت خدمات کسب‌وکار
"""
from rest_framework import serializers
from apps.businesses.models import Service, SubCategory


class SubCategoryBriefSerializer(serializers.ModelSerializer):
    """Serializer خلاصه برای زیردسته‌بندی"""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'category_name']


class ServiceListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست خدمات"""
    final_price = serializers.ReadOnlyField()
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    subcategory_icon = serializers.CharField(source='subcategory.category.icon', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description',
            'original_price', 'discount_percent', 'final_price',
            'has_deposit', 'deposit_amount',
            'duration_minutes', 'is_active',
            'reminder_days',
            'subcategory_name', 'subcategory_icon',
            'business_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ServiceDetailSerializer(serializers.ModelSerializer):
    """Serializer کامل برای جزئیات خدمت"""
    final_price = serializers.ReadOnlyField()
    subcategory = SubCategoryBriefSerializer(read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(),
        source='subcategory',
        write_only=True,
        required=False,
        allow_null=True
    )
    business_name = serializers.CharField(source='business.name', read_only=True)
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description',
            'original_price', 'discount_percent', 'final_price',
            'has_deposit', 'deposit_amount',
            'duration_minutes', 'is_active',
            'reminder_days',
            'subcategory', 'subcategory_id',
            'business_name', 'employee_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_employee_count(self, obj):
        """تعداد کارمندان ارائه‌دهنده این خدمت"""
        return obj.employees.filter(is_active=True).count()

    def validate(self, data):
        """اعتبارسنجی کلی"""
        # بررسی اینکه بیعانه بیشتر از قیمت نهایی نباشد
        original_price = data.get('original_price', getattr(self.instance, 'original_price', 0))
        discount_percent = data.get('discount_percent', getattr(self.instance, 'discount_percent', 0))
        deposit_amount = data.get('deposit_amount', getattr(self.instance, 'deposit_amount', 0))

        if original_price and discount_percent is not None:
            discount_amount = int(original_price * discount_percent / 100)
            final_price = max(0, original_price - discount_amount)

            if deposit_amount > final_price:
                raise serializers.ValidationError({
                    'deposit_amount': 'مبلغ بیعانه نمی‌تواند بیشتر از قیمت نهایی باشد'
                })

        return data

    def validate_name(self, value):
        """اعتبارسنجی نام خدمت"""
        if not value or not value.strip():
            raise serializers.ValidationError('نام خدمت الزامی است')
        if len(value.strip()) < 3:
            raise serializers.ValidationError('نام خدمت باید حداقل ۳ کاراکتر باشد')
        if len(value) > 150:
            raise serializers.ValidationError('نام خدمت نمی‌تواند بیشتر از ۱۵۰ کاراکتر باشد')
        return value.strip()

    def validate_original_price(self, value):
        """اعتبارسنجی قیمت اصلی"""
        if value < 0:
            raise serializers.ValidationError('قیمت نمی‌تواند منفی باشد')
        return value

    def validate_discount_percent(self, value):
        """اعتبارسنجی درصد تخفیف"""
        if value < 0 or value > 100:
            raise serializers.ValidationError('درصد تخفیف باید بین ۰ تا ۱۰۰ باشد')
        return value

    def validate_duration_minutes(self, value):
        """اعتبارسنجی مدت زمان"""
        if value < 15:
            raise serializers.ValidationError('مدت زمان باید حداقل ۱۵ دقیقه باشد')
        if value > 480:
            raise serializers.ValidationError('مدت زمان نمی‌تواند بیشتر از ۸ ساعت باشد')
        return value


class ServiceCreateSerializer(ServiceDetailSerializer):
    """Serializer برای ایجاد خدمت جدید"""

    def create(self, validated_data):
        """ایجاد خدمت جدید"""
        # اضافه کردن business از context
        request = self.context.get('request')
        validated_data['business'] = request.user.business
        return super().create(validated_data)


class ServiceUpdateSerializer(ServiceDetailSerializer):
    """Serializer برای بروزرسانی خدمت"""

    def update(self, instance, validated_data):
        """بروزرسانی خدمت"""
        # فقط صاحب کسب‌وکار می‌تواند ویرایش کند
        request = self.context.get('request')
        if instance.business.owner != request.user:
            raise serializers.ValidationError('شما اجازه ویرایش این خدمت را ندارید')

        return super().update(instance, validated_data)