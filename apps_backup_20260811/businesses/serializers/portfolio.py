"""
Serializers برای مدیریت نمونه‌کارها
"""
from rest_framework import serializers
from apps.businesses.models import Portfolio, PortfolioImage, Service


class PortfolioImageSerializer(serializers.ModelSerializer):
    """Serializer برای تصاویر نمونه‌کار"""

    class Meta:
        model = PortfolioImage
        fields = ['id', 'image', 'order']


class PortfolioListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست نمونه‌کارها"""
    images = PortfolioImageSerializer(many=True, read_only=True)
    cover_image = serializers.SerializerMethodField()
    images_count = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            'id', 'title', 'description',
            'is_active', 'order',
            'images', 'cover_image', 'images_count',
            'service_name', 'business_name',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def get_cover_image(self, obj):
        """دریافت اولین تصویر به عنوان کاور"""
        first_image = obj.images.order_by('order').first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None

    def get_images_count(self, obj):
        """تعداد تصاویر"""
        return obj.images.count()


class PortfolioDetailSerializer(serializers.ModelSerializer):
    """Serializer کامل برای جزئیات نمونه‌کار"""
    images = PortfolioImageSerializer(many=True, read_only=True)
    image_data = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=5
    )
    cover_image = serializers.SerializerMethodField()
    images_count = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='service',
        write_only=True,
        required=False,
        allow_null=True
    )
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            'id', 'title', 'description',
            'is_active', 'order',
            'images', 'image_data',
            'cover_image', 'images_count',
            'service', 'service_id', 'service_name',
            'business_name',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def get_cover_image(self, obj):
        """دریافت اولین تصویر به عنوان کاور"""
        first_image = obj.images.order_by('order').first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None

    def get_images_count(self, obj):
        """تعداد تصاویر"""
        return obj.images.count()

    def validate_title(self, value):
        """اعتبارسنجی عنوان"""
        if not value or not value.strip():
            raise serializers.ValidationError('عنوان نمونه‌کار الزامی است')
        if len(value.strip()) < 3:
            raise serializers.ValidationError('عنوان باید حداقل ۳ کاراکتر باشد')
        if len(value) > 150:
            raise serializers.ValidationError('عنوان نمی‌تواند بیشتر از ۱۵۰ کاراکتر باشد')
        return value.strip()

    def validate_description(self, value):
        """اعتبارسنجی توضیحات"""
        if value and len(value) > 500:
            raise serializers.ValidationError('توضیحات نمی‌تواند بیشتر از ۵۰۰ کاراکتر باشد')
        return value

    def validate_image_data(self, value):
        """اعتبارسنجی تصاویر - حداکثر ۵ تصویر"""
        if len(value) > 5:
            raise serializers.ValidationError('حداکثر ۵ تصویر برای هر نمونه‌کار مجاز است')

        # بررسی حجم و فرمت هر تصویر
        for image in value:
            # حداکثر ۵ مگابایت
            if image.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    f'حجم تصویر {image.name} نمی‌تواند بیشتر از ۵ مگابایت باشد'
                )

            # فرمت‌های مجاز
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            ext = image.name.lower().split('.')[-1]
            if f'.{ext}' not in valid_extensions:
                raise serializers.ValidationError(
                    f'فرمت تصویر {image.name} نامعتبر است. فرمت‌های مجاز: {", ".join(valid_extensions)}'
                )

        return value

    def validate_service_id(self, value):
        """اعتبارسنجی خدمت - فقط خدمات همان کسب‌وکار"""
        if value:
            request = self.context.get('request')
            business = request.user.business

            if value.business != business:
                raise serializers.ValidationError('این خدمت متعلق به کسب‌وکار شما نیست')

        return value


class PortfolioCreateSerializer(PortfolioDetailSerializer):
    """Serializer برای ایجاد نمونه‌کار جدید"""

    def create(self, validated_data):
        """ایجاد نمونه‌کار جدید"""
        request = self.context.get('request')
        image_data = validated_data.pop('image_data', [])
        validated_data['business'] = request.user.business

        portfolio = Portfolio.objects.create(**validated_data)

        # ذخیره تصاویر
        for order, image in enumerate(image_data):
            PortfolioImage.objects.create(
                portfolio=portfolio,
                image=image,
                order=order
            )

        return portfolio


class PortfolioUpdateSerializer(PortfolioDetailSerializer):
    """Serializer برای بروزرسانی نمونه‌کار"""

    def update(self, instance, validated_data):
        """بروزرسانی نمونه‌کار"""
        request = self.context.get('request')
        if instance.business.owner != request.user:
            raise serializers.ValidationError('شما اجازه ویرایش این نمونه‌کار را ندارید')

        image_data = validated_data.pop('image_data', None)

        # بروزرسانی فیلدها
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # بروزرسانی تصاویر (اگر ارائه شده باشد)
        if image_data is not None:
            # حذف تصاویر قبلی
            instance.images.all().delete()

            # ذخیره تصاویر جدید
            for order, image in enumerate(image_data):
                PortfolioImage.objects.create(
                    portfolio=instance,
                    image=image,
                    order=order
                )

        return instance