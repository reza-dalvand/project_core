"""
Serializers برای نمونه‌کارها
"""
from rest_framework import serializers
from apps.portfolios.models import Portfolio, PortfolioImage


class PortfolioImageSerializer(serializers.ModelSerializer):
    """Serializer تصاویر نمونه‌کار"""
    class Meta:
        model = PortfolioImage
        fields = ['id', 'image', 'sort_order']
        read_only_fields = ['id', 'image', 'sort_order']


class PortfolioListSerializer(serializers.ModelSerializer):
    """Serializer لیست نمونه‌کارها"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    sub_service_name = serializers.CharField(
        source='sub_service.name', read_only=True
    )
    images = PortfolioImageSerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            'id', 'title', 'description',
            'category', 'category_name',
            'sub_service', 'sub_service_name',
            'business', 'business_name', 'business_logo',
            'cover_image_url', 'images',
            'created_at',
        ]
        read_only_fields = fields

    def get_business_logo(self, obj):
        request = self.context.get('request')
        if obj.business.logo and request:
            return request.build_absolute_uri(obj.business.logo.url)
        return None

    def get_cover_image_url(self, obj):
        request = self.context.get('request')
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None


class PortfolioDetailSerializer(PortfolioListSerializer):
    """Serializer جزئیات نمونه‌کار"""
    business_booking_slug = serializers.CharField(
        source='business.booking_slug', read_only=True
    )

    class Meta(PortfolioListSerializer.Meta):
        fields = PortfolioListSerializer.Meta.fields + [
            'business_booking_slug',
        ]


class PortfolioCreateSerializer(serializers.ModelSerializer):
    """Serializer ایجاد نمونه‌کار"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=3,
    )

    class Meta:
        model = Portfolio
        fields = [
            'title', 'description',
            'category', 'sub_service',
            'cover_image', 'images',
        ]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('عنوان الزامی است')
        return value.strip()

    def validate_description(self, value):
        if value and len(value) > 300:
            raise serializers.ValidationError(
                'توضیحات نمی‌تواند بیشتر از ۳۰۰ کاراکتر باشد'
            )
        return value

    def validate_images(self, value):
        if value and len(value) > 3:
            raise serializers.ValidationError('حداکثر ۳ تصویر مجاز است')
        return value

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        request = self.context.get('request')
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            raise serializers.ValidationError(
                'کسب‌وکار تایید شده‌ای یافت نشد'
            )

        validated_data['business'] = business
        portfolio = Portfolio.objects.create(**validated_data)

        # ذخیره تصاویر
        for i, image in enumerate(images):
            PortfolioImage.objects.create(
                portfolio=portfolio,
                image=image,
                sort_order=i,
            )

        return portfolio


class PortfolioUpdateSerializer(serializers.ModelSerializer):
    """Serializer ویرایش نمونه‌کار"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=3,
    )
    
    class Meta:
        model = Portfolio
        fields = [
            'title', 'description',
            'category', 'sub_service',
            'cover_image', 'images',
        ]
    
    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('عنوان الزامی است')
        return value.strip()
    
    def validate_description(self, value):
        if value and len(value) > 300:
            raise serializers.ValidationError(
                'توضیحات نمی‌تواند بیشتر از ۳۰۰ کاراکتر باشد'
            )
        return value
    
    def validate_images(self, value):
        if value and len(value) > 3:
            raise serializers.ValidationError('حداکثر ۳ تصویر مجاز است')
        return value
    
    def update(self, instance, validated_data):
        images = validated_data.pop('images', None)
        
        # بروزرسانی فیلدهای ساده
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # بروزرسانی تصاویر (اگر ارسال شده باشند)
        if images is not None:
            # حذف تصاویر قبلی
            instance.images.all().delete()
            # افزودن تصاویر جدید
            for i, image in enumerate(images):
                PortfolioImage.objects.create(
                    portfolio=instance,
                    image=image,
                    sort_order=i,
                )
        
        return instance