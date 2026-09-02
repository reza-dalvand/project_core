"""
Serializers برای نمونه‌کارها
"""
import os
import requests
import tempfile
from django.core.files.base import ContentFile
from rest_framework import serializers
from apps.portfolios.models import Portfolio, PortfolioImage


class PortfolioImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioImage
        fields = ['id', 'image', 'image_url', 'sort_order']
        read_only_fields = ['image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


# apps/portfolios/serializers/__init__.py — فقط لیست‌سریالایزر

class PortfolioListSerializer(serializers.ModelSerializer):
    """Serializer لیست نمونه‌کارها برای ویترین"""
    business_name = serializers.CharField(
        source='business.name', read_only=True
    )
    business_logo = serializers.SerializerMethodField()
    # ✅ فیلد جدید: عکس صاحب کسب‌وکار
    business_owner_photo = serializers.SerializerMethodField()
    business_booking_slug = serializers.CharField(
        source='business.booking_slug', read_only=True
    )
    category_name = serializers.CharField(
        source='category.name', read_only=True
    )
    sub_service_name = serializers.CharField(
        source='sub_service.name', read_only=True
    )
    images = PortfolioImageSerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            'id', 'title', 'description',
            'business', 'business_name', 'business_logo',
            'business_owner_photo',  # ✅ اضافه شد
            'business_booking_slug',
            'category', 'category_name',
            'sub_service', 'sub_service_name',
            'cover_image', 'cover_image_url',
            'images', 'created_at',
        ]
        read_only_fields = fields

    def get_business_logo(self, obj):
        request = self.context.get('request')
        if obj.business.logo and request:
            return request.build_absolute_uri(obj.business.logo.url)
        return None

    # ✅ متد جدید
    def get_business_owner_photo(self, obj):
        request = self.context.get('request')
        if obj.business.owner_photo and request:
            return request.build_absolute_uri(obj.business.owner_photo.url)
        return None

    def get_cover_image_url(self, obj):
        request = self.context.get('request')
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None
    
class PortfolioDetailSerializer(PortfolioListSerializer):
    business_address = serializers.CharField(source='business.address', read_only=True)
    business_city = serializers.CharField(source='business.city.name', read_only=True)

    class Meta(PortfolioListSerializer.Meta):
        fields = PortfolioListSerializer.Meta.fields + [
            'business_address', 'business_city',
        ]


class PortfolioCreateSerializer(serializers.Serializer):
    """
    Serializer ایجاد نمونه‌کار — فقط آپلود فایل
    حداقل یک تصویر اجباری است.
    """
    title = serializers.CharField(max_length=100)
    description = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=''
    )
    category = serializers.IntegerField(required=True)
    sub_service = serializers.IntegerField(required=True)

    # ✅ تصویر کاور — اجباری
    cover_image = serializers.ImageField(required=True)

    # ✅ تصاویر گالری — حداقل ۱ فایل، حداکثر ۳
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=True,
        allow_empty=False,
        min_length=1,
        max_length=3,
    )

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('عنوان نمونه‌کار الزامی است')
        if len(value.strip()) < 3:
            raise serializers.ValidationError('عنوان باید حداقل ۳ کاراکتر باشد')
        return value.strip()

    def validate(self, data):
        from apps.categories.models import ServiceCategory, SubService

        cat_id = data.get('category')
        sub_id = data.get('sub_service')

        if not cat_id:
            raise serializers.ValidationError({
                'category': 'دسته‌بندی خدمات را انتخاب کنید'
            })
        if not sub_id:
            raise serializers.ValidationError({
                'sub_service': 'نوع خدمت را انتخاب کنید'
            })

        try:
            category = ServiceCategory.objects.get(id=cat_id, is_active=True)
        except ServiceCategory.DoesNotExist:
            raise serializers.ValidationError({
                'category': 'دسته‌بندی یافت نشد'
            })

        try:
            sub_service = SubService.objects.get(
                id=sub_id, category=category, is_active=True
            )
        except SubService.DoesNotExist:
            raise serializers.ValidationError({
                'sub_service': 'زیرخدمت یافت نشد یا با دسته‌بندی مطابقت ندارد'
            })

        data['_category'] = category
        data['_sub_service'] = sub_service
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        if not business:
            raise serializers.ValidationError(
                'کسب‌وکار تایید شده‌ای یافت نشد'
            )

        category = validated_data.pop('_category')
        sub_service = validated_data.pop('_sub_service')
        cover_image = validated_data.pop('cover_image')
        image_files = validated_data.pop('images', [])

        portfolio = Portfolio.objects.create(
            business=business,
            category=category,
            sub_service=sub_service,
            title=validated_data.get('title', ''),
            description=validated_data.get('description', ''),
            cover_image=cover_image,  # ✅ فایل واقعی
        )

        # ذخیره تصاویر گالری
        for i, img_file in enumerate(image_files):
            PortfolioImage.objects.create(
                portfolio=portfolio,
                image=img_file,  # ✅ فایل واقعی
                sort_order=i,
            )

        return portfolio




class PortfolioUpdateSerializer(serializers.Serializer):
    """Serializer ویرایش نمونه‌کار — با پشتیبانی از فایل"""
    title = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(
        max_length=300, required=False, allow_blank=True
    )
    category = serializers.IntegerField(required=False)
    sub_service = serializers.IntegerField(required=False)
    cover_image = serializers.ImageField(required=False)
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
        max_length=3,
    )

    def validate_category(self, value):
        if value is not None:
            from apps.categories.models import ServiceCategory
            if not ServiceCategory.objects.filter(id=value, is_active=True).exists():
                raise serializers.ValidationError('دسته‌بندی یافت نشد')
        return value

    def validate_sub_service(self, value):
        if value is not None:
            from apps.categories.models import SubService
            if not SubService.objects.filter(id=value, is_active=True).exists():
                raise serializers.ValidationError('زیرخدمت یافت نشد')
        return value

    def update(self, instance, validated_data):
        from apps.categories.models import ServiceCategory, SubService

        # ─── بروزرسانی فیلدهای ساده ───
        cat_id = validated_data.pop('category', None)
        sub_id = validated_data.pop('sub_service', None)

        if cat_id is not None:
            try:
                instance.category = ServiceCategory.objects.get(
                    id=cat_id, is_active=True
                )
            except ServiceCategory.DoesNotExist:
                pass

        if sub_id is not None:
            try:
                instance.sub_service = SubService.objects.get(
                    id=sub_id, is_active=True
                )
            except SubService.DoesNotExist:
                pass

        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'description' in validated_data:
            instance.description = validated_data['description']

        # ─── بروزرسانی کاور ───
        cover_image = validated_data.pop('cover_image', None)
        if cover_image:
            # حذف فایل قبلی از دیسک
            if instance.cover_image:
                instance.cover_image.delete(save=False)
            instance.cover_image = cover_image

        instance.save()

        # ─── بروزرسانی تصاویر گالری ───
        # ✅ فقط اگر تصاویر جدید ارسال شده باشند
        image_files = validated_data.pop('images', None)
        if image_files is not None and len(image_files) > 0:
            # حذف تصاویر قبلی از دیسک
            for old_img in instance.images.all():
                old_img.image.delete(save=False)
            instance.images.all().delete()
            # ایجاد تصاویر جدید
            for i, img_file in enumerate(image_files):
                PortfolioImage.objects.create(
                    portfolio=instance,
                    image=img_file,
                    sort_order=i,
                )
        # ✅ اگر images ارسال نشده یا خالی باشد، تصاویر قبلی حفظ می‌شوند

        return instance