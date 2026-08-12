"""
Serializers برای ویترین / اکسپلور
"""
from rest_framework import serializers
from apps.explore.models import ExplorePost, PostImage


class PostImageSerializer(serializers.ModelSerializer):
    """Serializer تصاویر پست"""
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'sort_order']
        read_only_fields = ['id', 'image', 'sort_order']


class ExplorePostListSerializer(serializers.ModelSerializer):
    """Serializer لیست پست‌های ویترین"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.SerializerMethodField()
    business_booking_slug = serializers.CharField(
        source='business.booking_slug', read_only=True
    )
    main_category_name = serializers.CharField(
        source='main_category.name', read_only=True, default=None
    )
    sub_category_name = serializers.CharField(
        source='sub_category.name', read_only=True, default=None
    )
    images = PostImageSerializer(many=True, read_only=True)
    first_image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = ExplorePost
        fields = [
            'id', 'caption', 'source',
            'business', 'business_name', 'business_logo',
            'business_booking_slug',
            'main_category', 'main_category_name',
            'sub_category', 'sub_category_name',
            'is_pinned', 'images', 'first_image',
            'is_favorited',
            'created_at',
        ]
        read_only_fields = fields

    def get_business_logo(self, obj):
        request = self.context.get('request')
        if obj.business.logo and request:
            return request.build_absolute_uri(obj.business.logo.url)
        return None

    def get_first_image(self, obj):
        request = self.context.get('request')
        first = obj.images.order_by('sort_order').first()
        if first and request:
            return request.build_absolute_uri(first.image.url)
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False


class ExplorePostDetailSerializer(ExplorePostListSerializer):
    """Serializer جزئیات پست"""
    business_address = serializers.CharField(
        source='business.address', read_only=True
    )
    business_city = serializers.CharField(
        source='business.city.name', read_only=True
    )

    class Meta(ExplorePostListSerializer.Meta):
        fields = ExplorePostListSerializer.Meta.fields + [
            'business_address', 'business_city',
        ]


class ExplorePostCreateSerializer(serializers.ModelSerializer):
    """Serializer ایجاد پست"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=5,
    )

    class Meta:
        model = ExplorePost
        fields = [
            'caption', 'main_category', 'sub_category',
            'images',
        ]

    def validate_caption(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('کپشن الزامی است')
        if len(value.strip()) < 10:
            raise serializers.ValidationError('کپشن باید حداقل ۱۰ کاراکتر باشد')
        return value.strip()

    def validate_images(self, value):
        if value and len(value) > 5:
            raise serializers.ValidationError('حداکثر ۵ تصویر مجاز است')
        return value

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        request = self.context.get('request')
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            raise serializers.ValidationError(
                'کسب‌وکار تایید شده‌ای برای شما یافت نشد'
            )

        validated_data['business'] = business
        validated_data['source'] = ExplorePost.Source.BUSINESS
        post = ExplorePost.objects.create(**validated_data)

        # ذخیره تصاویر
        for i, image in enumerate(images):
            PostImage.objects.create(
                post=post,
                image=image,
                sort_order=i,
            )

        return post