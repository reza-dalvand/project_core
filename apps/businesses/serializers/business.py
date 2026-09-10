"""
Serializers برای کسب‌وکار
"""
from rest_framework import serializers
from apps.businesses.models import Business, BusinessGallery
from apps.categories.serializers import BusinessCategorySerializer
from apps.locations.serializers import ProvinceSerializer, CitySerializer


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
        if cover_image:
            validated_data['cover_image'] = cover_image
        if owner_photo:
            validated_data['owner_photo'] = owner_photo
        if logo:
            validated_data['logo'] = logo
        business = Business.objects.create(**validated_data)
        return business


class BusinessDetailSerializer(serializers.ModelSerializer):
    category = BusinessCategorySerializer(read_only=True)
    province = ProvinceSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    owner_name = serializers.SerializerMethodField()
    gallery = BusinessGallerySerializer(many=True, read_only=True)
    services = serializers.SerializerMethodField()
    verified_name = serializers.SerializerMethodField()
    national_id = serializers.SerializerMethodField()
    is_national_id_verified = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            'id', 'name', 'category', 'province', 'city',
            'address', 'phone', 'working_hours', 'about',
            'latitude', 'longitude',
            'cover_image', 'owner_photo', 'logo',
            'status', 'is_active', 'is_vip', 'vip_expires_at',
            'rating', 'reviews_count',
            'booking_slug', 'booking_link_clicks',
            'gallery',
            'services',
            'owner_name', 'created_at',
            'bank_info_registered', 'bank_info_verified',
            'bank_owner_name',
            'bank_national_id',
            'bank_name',
            'bank_id',
            'bank_sheba',
            'bank_card_number',
            'bank_account_number',
            'verified_name',
            'national_id',
            'is_national_id_verified',
            'is_suspended',
            'suspension_reason',
        ]

    def get_owner_name(self, obj):
        return obj.owner.full_name

    def get_verified_name(self, obj):
        return obj.verified_name or obj.owner.verified_name or ''

    def get_national_id(self, obj):
        return obj.national_id or obj.owner.national_id or ''

    def get_is_national_id_verified(self, obj):
        return bool(obj.is_national_id_verified or obj.owner.is_national_id_verified)

    def get_services(self, obj):
        from apps.services.serializers import ServiceListSerializer
        services = obj.services.filter(is_active=True)
        return ServiceListSerializer(services, many=True).data


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
    """
    Serializer اطلاعات بانکی کسب‌وکار

    ✅ تغییر: اعتبارسنجی مقایسه‌ای نام صاحب حساب حذف شد.
    نام صاحب حساب مستقیماً توسط کاربر وارد و ذخیره می‌شود.
    اعتبارسنجی‌های مقایسه‌ای (مقایسه با کد ملی، وضعیت کسب‌وکار و ...)
    حذف شده‌اند. فقط اعتبارسنجی فرمت (شبا، کارت) باقی مانده است.
    """

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