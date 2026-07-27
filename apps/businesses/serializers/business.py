"""
Serializers مربوط به ثبت و مدیریت کسب‌وکار
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.businesses.models import (
    Business, Category, SubCategory, Province, City,
    Service, Employee, Portfolio, PortfolioImage
)
from apps.core.validators import validate_national_id

User = get_user_model()


# ═══════════════════════════════════════════════
#   Lookup Serializers (برای Dropdown ها)
# ═══════════════════════════════════════════════

class ProvinceSerializer(serializers.ModelSerializer):
    """Serializer برای استان‌ها"""

    class Meta:
        model = Province
        fields = ['id', 'name', 'slug', 'order']


class CitySerializer(serializers.ModelSerializer):
    """Serializer برای شهرها"""
    province_name = serializers.CharField(source='province.name', read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name', 'slug', 'province', 'province_name', 'order']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer برای دسته‌بندی‌ها"""
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'color', 'description', 'order', 'subcategories']

    def get_subcategories(self, obj):
        """گرفتن زیردسته‌های فعال"""
        subcats = obj.subcategories.filter(is_active=True).order_by('order')
        return SubCategorySerializer(subcats, many=True).data


class SubCategorySerializer(serializers.ModelSerializer):
    """Serializer برای زیردسته‌بندی‌ها"""

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'category', 'order']


# ═══════════════════════════════════════════════
#   National ID Verification
# ═══════════════════════════════════════════════

class NationalIdVerificationSerializer(serializers.Serializer):
    """Serializer برای استعلام کد ملی از شاهکار"""
    national_id = serializers.CharField(max_length=10, min_length=10)

    def validate_national_id(self, value):
        """اعتبارسنجی کد ملی"""
        try:
            return validate_national_id(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))


class NationalIdVerificationResponseSerializer(serializers.Serializer):
    """پاسخ استعلام کد ملی"""
    success = serializers.BooleanField()
    verified_name = serializers.CharField()
    national_id = serializers.CharField()
    phone_display = serializers.CharField()
    message = serializers.CharField()


# ═══════════════════════════════════════════════
#   Business Creation (Wizard)
# ═══════════════════════════════════════════════

class BusinessCreateSerializer(serializers.ModelSerializer):
    """
    Serializer برای ایجاد کسب‌وکار (مرحله ۱ و ۲ Wizard)

    مرحله ۱: اطلاعات پایه
    - name, category, province, city, address, location, cover_image

    مرحله ۲: احراز هویت
    - national_id, verified_name

    مرحله ۳: پذیرش قوانین (فقط کلاینت)
    """

    # فیلدهای اضافی برای مرحله ۱
    cover_image = serializers.ImageField(
        required=False,
        allow_null=True,
        write_only=True
    )
    owner_photo = serializers.ImageField(
        required=False,
        allow_null=True,
        write_only=True
    )

    # فیلدهای Lookup
    category_name = serializers.CharField(source='category.name', read_only=True)
    province_name = serializers.CharField(source='province.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)

    # فیلدهای محاسباتی
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Business
        fields = [
            # شناسه
            'id', 'slug',

            # اطلاعات پایه
            'name', 'category', 'category_name',
            'province', 'province_name',
            'city', 'city_name',
            'address', 'latitude', 'longitude',
            'phone',

            # تصاویر
            'cover_image', 'owner_photo',
            'logo', 'cover', 'owner_photo',

            # احراز هویت
            'owner',

            # وضعیت
            'status', 'approved_at',

            # تاریخ‌ها
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'owner', 'status', 'approved_at',
            'created_at', 'updated_at', 'logo', 'cover', 'owner_photo'
        ]

    def validate_category(self, value):
        """بررسی فعال بودن دسته‌بندی"""
        if not value.is_active:
            raise serializers.ValidationError('این دسته‌بندی فعال نیست')
        return value

    def validate_province(self, value):
        """بررسی وجود استان"""
        return value

    def validate_city(self, value):
        """بررسی تعلق شهر به استان"""
        province = self.initial_data.get('province')
        if province and value.province_id != int(province):
            raise serializers.ValidationError('این شهر متعلق به استان انتخاب شده نیست')
        return value

    def validate_address(self, value):
        """بررسی طول آدرس"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError('آدرس باید حداقل ۱۰ کاراکتر باشد')
        if len(value) > 500:
            raise serializers.ValidationError('آدرس نمی‌تواند بیشتر از ۵۰۰ کاراکتر باشد')
        return value.strip()

    def validate(self, data):
        """اعتبارسنجی کلی"""
        # بررسی اینکه کاربر قبلاً کسب‌وکار نداشته باشد
        user = self.context['request'].user
        if hasattr(user, 'business'):
            raise serializers.ValidationError({
                'non_field_errors': ['شما قبلاً یک کسب‌وکار ثبت کرده‌اید']
            })

        # بررسی تایید کد ملی کاربر
        if not user.national_id_verified:
            raise serializers.ValidationError({
                'non_field_errors': ['ابتدا باید کد ملی خود را تایید کنید']
            })

        return data

    def create(self, validated_data):
        """ایجاد کسب‌وکار"""
        # استخراج تصاویر
        cover_image = validated_data.pop('cover_image', None)
        owner_photo = validated_data.pop('owner_photo', None)

        # تنظیم owner
        user = self.context['request'].user
        validated_data['owner'] = user

        # وضعیت اولیه: pending
        validated_data['status'] = Business.Status.PENDING

        # ایجاد کسب‌وکار
        business = Business.objects.create(**validated_data)

        # ذخیره تصاویر
        if cover_image:
            business.cover = cover_image
        if owner_photo:
            business.owner_photo = owner_photo

        if cover_image or owner_photo:
            business.save()

        return business


# ═══════════════════════════════════════════════
#   Business Detail & Update
# ═══════════════════════════════════════════════

class BusinessDetailSerializer(serializers.ModelSerializer):
    """Serializer برای نمایش جزئیات کسب‌وکار"""

    category = CategorySerializer(read_only=True)
    province = ProvinceSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    owner_phone = serializers.CharField(source='owner.phone', read_only=True)

    class Meta:
        model = Business
        fields = [
            'id', 'slug', 'name',
            'category', 'province', 'city',
            'address', 'latitude', 'longitude',
            'phone', 'working_hours_text',
            'logo', 'cover', 'owner_photo',
            'about',
            'owner_name', 'owner_phone',
            'status', 'is_vip', 'is_featured',
            'rating_avg', 'rating_count',
            'services_count', 'bookings_count',
            'booking_link',
            'approved_at', 'created_at', 'updated_at',
        ]


class BusinessUpdateSerializer(serializers.ModelSerializer):
    """Serializer برای بروزرسانی کسب‌وکار"""

    cover_image = serializers.ImageField(
        required=False,
        allow_null=True,
        write_only=True
    )
    owner_photo = serializers.ImageField(
        required=False,
        allow_null=True,
        write_only=True
    )

    class Meta:
        model = Business
        fields = [
            'name', 'category', 'province', 'city',
            'address', 'latitude', 'longitude',
            'phone', 'working_hours_text',
            'cover_image', 'owner_photo',
            'about',
        ]

    def update(self, instance, validated_data):
        """بروزرسانی کسب‌وکار"""
        cover_image = validated_data.pop('cover_image', None)
        owner_photo = validated_data.pop('owner_photo', None)

        # بروزرسانی فیلدها
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # بروزرسانی تصاویر
        if cover_image:
            instance.cover = cover_image
        if owner_photo:
            instance.owner_photo = owner_photo

        instance.save()
        return instance


# ═══════════════════════════════════════════════
#   Business Status
# ═══════════════════════════════════════════════

class BusinessStatusSerializer(serializers.Serializer):
    """Serializer برای وضعیت کسب‌وکار"""
    has_business = serializers.BooleanField()
    business_id = serializers.IntegerField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    status_display = serializers.CharField(allow_null=True)
    rejection_reason = serializers.CharField(allow_null=True)
    approved_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)


# ═══════════════════════════════════════════════
#   Image Upload
# ═══════════════════════════════════════════════

class ImageUploadSerializer(serializers.Serializer):
    """Serializer برای آپلود تصاویر"""

    image = serializers.ImageField()
    image_type = serializers.ChoiceField(
        choices=[
            ('cover', 'کاور کسب‌وکار'),
            ('logo', 'لوگو'),
            ('owner_photo', 'عکس صاحب کسب‌وکار'),
        ]
    )

    def validate_image(self, value):
        """اعتبارسنجی تصویر"""
        # بررسی حجم (حداکثر ۵ مگابایت)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('حجم تصویر نمی‌تواند بیشتر از ۵ مگابایت باشد')

        # بررسی فرمت
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        ext = value.name.lower().split('.')[-1]
        if f'.{ext}' not in valid_extensions:
            raise serializers.ValidationError(f'فرمت تصویر باید یکی از {", ".join(valid_extensions)} باشد')

        return value


class ImageUploadResponseSerializer(serializers.Serializer):
    """پاسخ آپلود تصویر"""
    success = serializers.BooleanField()
    image_url = serializers.URLField()
    image_type = serializers.CharField()
    message = serializers.CharField()


# ─── این serializer را به فایل business.py اضافه کنید ───

class ServiceBriefSerializer(serializers.ModelSerializer):
    """Serializer خلاصه برای خدمت (استفاده در Appointment)"""
    subcategory_name = serializers.CharField(
        source='subcategory.name', read_only=True, default=None
    )

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'original_price', 'discount_percent',
            'final_price', 'duration_minutes', 'has_deposit',
            'deposit_amount', 'subcategory_name',
        ]