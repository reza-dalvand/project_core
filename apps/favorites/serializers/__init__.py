# apps/favorites/serializers/__init__.py
# اطمینان از وجود FavoriteBusinessSerializer

"""
Serializers برای علاقه‌مندی‌ها
"""
from rest_framework import serializers
from apps.favorites.models import FavoriteBusiness


class FavoriteBusinessSerializer(serializers.ModelSerializer):
    """Serializer برای علاقه‌مندی به کسب‌وکار"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.SerializerMethodField()
    business_cover = serializers.SerializerMethodField()  # ✅ جدید
    business_category = serializers.CharField(
        source='business.category.name', read_only=True, default=''
    )
    business_city = serializers.CharField(
        source='business.city.name', read_only=True, default=''
    )
    business_slug = serializers.CharField(source='business.booking_slug', read_only=True)  # ✅ جدید

    class Meta:
        model = FavoriteBusiness
        fields = [
            'id', 'business', 'business_name', 'business_logo', 'business_cover',
            'business_category', 'business_city', 'business_slug',
            'created_at',
        ]

    def get_business_logo(self, obj):
        request = self.context.get('request')
        if obj.business.logo and request:
            return request.build_absolute_uri(obj.business.logo.url)
        return None

    def get_business_cover(self, obj):
        """✅ جدید: تصویر کاور کسب‌وکار"""
        request = self.context.get('request')
        # اول cover_image را چک کن
        if hasattr(obj.business, 'cover_image') and obj.business.cover_image and request:
            return request.build_absolute_uri(obj.business.cover_image.url)
        # اگر cover نبود، اولین تصویر گالری
        if hasattr(obj.business, 'gallery') and request:
            first_gallery = obj.business.gallery.first()
            if first_gallery and first_gallery.image:
                return request.build_absolute_uri(first_gallery.image.url)
        # Fallback به logo
        return self.get_business_logo(obj)