"""
Serializers مربوط به ثبت و مدیریت کسب‌وکار
هر کاربر فقط یک کسب‌وکار — بدون تیم
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.businesses.models import Business, BusinessGallery
# ❌ BusinessTeamMember حذف شد
from apps.categories.serializers import BusinessCategorySerializer
from apps.locations.serializers import ProvinceSerializer, CitySerializer

User = get_user_model()


class BusinessGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessGallery
        fields = ['id', 'image', 'sort_order']


# ❌ BusinessTeamMemberSerializer حذف شد


class BusinessCreateSerializer(serializers.ModelSerializer):
    cover_image = serializers.ImageField(required=False, allow_null=True, write_only=True)
    owner_photo = serializers.ImageField(required=False, allow_null=True, write_only=True)
    logo = serializers.ImageField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Business
        fields = [
            'id', 'name', 'category', 'province', 'city',
            'address', 'phone', 'working_hours', 'about',
            'latitude', 'longitude',
            'cover_image', 'owner_photo', 'logo',
            'booking_slug', 'status', 'created_at',
        ]
        read_only_fields = ['id', 'booking_slug', 'status', 'created_at']

    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError('این دسته‌بندی فعال نیست')
        return value

    def validate_address(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError('آدرس باید حداقل ۱۰ کاراکتر باشد')
        return value.strip()

    def validate(self, data):
        user = self.context['request'].user
        if user.businesses.filter(is_active=True).exists():
            raise serializers.ValidationError({
                'non_field_errors': ['شما قبلاً یک کسب‌وکار ثبت کرده‌اید']
            })
        if not user.is_national_id_verified:
            raise serializers.ValidationError({
                'non_field_errors': ['ابتدا باید کد ملی خود را تایید کنید']
            })
        return data

    def create(self, validated_data):
        cover_image = validated_data.pop('cover_image', None)
        owner_photo = validated_data.pop('owner_photo', None)
        logo = validated_data.pop('logo', None)
        user = self.context['request'].user
        validated_data['owner'] = user
        validated_data['status'] = Business.Status.PENDING
        business = Business.objects.create(**validated_data)
        if cover_image:
            business.cover_image = cover_image
        if owner_photo:
            business.owner_photo = owner_photo
        if logo:
            business.logo = logo
        if any([cover_image, owner_photo, logo]):
            business.save()
        return business


class BusinessDetailSerializer(serializers.ModelSerializer):
    category = BusinessCategorySerializer(read_only=True)
    province = ProvinceSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    owner_name = serializers.SerializerMethodField()
    gallery = BusinessGallerySerializer(many=True, read_only=True)

    class Meta:
        model = Business
        fields = [
            'id', 'name', 'category', 'province', 'city',
            'address', 'phone', 'working_hours', 'about',
            'latitude', 'longitude',
            'cover_image', 'owner_photo', 'logo',
            'status', 'is_vip', 'vip_expires_at',
            'rating', 'reviews_count',
            'booking_slug', 'booking_link_clicks',
            'gallery',
            'owner_name', 'created_at',
            'bank_info_registered', 'bank_info_verified',
            'verified_name',
            'owner_name', 'created_at',
        ]

    def get_owner_name(self, obj):
        return obj.owner.full_name


class BusinessUpdateSerializer(serializers.ModelSerializer):
    cover_image = serializers.ImageField(required=False, allow_null=True, write_only=True)
    owner_photo = serializers.ImageField(required=False, allow_null=True, write_only=True)
    logo = serializers.ImageField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Business
        fields = [
            'name', 'category', 'province', 'city',
            'address', 'phone', 'working_hours', 'about',
            'latitude', 'longitude',
            'cover_image', 'owner_photo', 'logo',
        ]

    def update(self, instance, validated_data):
        cover_image = validated_data.pop('cover_image', None)
        owner_photo = validated_data.pop('owner_photo', None)
        logo = validated_data.pop('logo', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if cover_image:
            instance.cover_image = cover_image
        if owner_photo:
            instance.owner_photo = owner_photo
        if logo:
            instance.logo = logo
        instance.save()
        return instance


class BusinessBankInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            'bank_owner_name', 'bank_national_id', 'bank_name',
            'bank_id', 'bank_sheba', 'bank_card_number',
            'bank_account_number', 'bank_info_registered',
            'bank_info_verified',
        ]
        read_only_fields = ['bank_info_verified']

    def validate_bank_sheba(self, value):
        if value:
            from apps.core.validators import validate_sheba
            try:
                return validate_sheba(value)
            except Exception as e:
                raise serializers.ValidationError(str(e))
        return value

    def validate_bank_card_number(self, value):
        if value:
            from apps.core.validators import validate_card_number
            try:
                return validate_card_number(value)
            except Exception as e:
                raise serializers.ValidationError(str(e))
        return value

    def validate(self, data):
        user = self.context['request'].user
        if user.verified_name and data.get('bank_owner_name'):
            if data['bank_owner_name'].strip() != user.verified_name.strip():
                raise serializers.ValidationError({
                    'bank_owner_name': 'نام صاحب حساب باید با نام تایید شده مطابقت داشته باشد'
                })
        return data

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.bank_info_registered = True
        instance.save()
        return instance


class BusinessStatusSerializer(serializers.Serializer):
    has_business = serializers.BooleanField()
    business_id = serializers.IntegerField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    status_display = serializers.CharField(allow_null=True)
    rejection_reason = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)


class BusinessListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = Business
        fields = [
            'id', 'name', 'category_name', 'city_name',
            'address', 'logo', 'cover_image',
            'rating', 'reviews_count',
            'booking_slug', 'is_vip',
            'created_at',
        ]


class BusinessGallerySerializer(serializers.ModelSerializer):
    """Serializer تصاویر گالری"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessGallery
        fields = ['id', 'image', 'image_url', 'sort_order']
        read_only_fields = ['image_url']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class BusinessGalleryUploadSerializer(serializers.Serializer):
    """Serializer آپلود تصویر گالری"""
    image = serializers.ImageField()
    sort_order = serializers.IntegerField(required=False, default=0)
    
    def validate_image(self, value):
        if value.size > 5 * 1024 * 1024:  # 5MB
            raise serializers.ValidationError('حجم تصویر نباید بیشتر از ۵ مگابایت باشد')
        return value