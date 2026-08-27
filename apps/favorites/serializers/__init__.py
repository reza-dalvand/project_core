"""
Serializers برای علاقه‌مندی‌ها — نسخه نهایی (فاز ۸)
"""
from rest_framework import serializers
from apps.favorites.models import FavoriteBusiness, FavoritePost


class FavoriteBusinessSerializer(serializers.ModelSerializer):
    """Serializer برای علاقه‌مندی به کسب‌وکار"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.SerializerMethodField()
    # ✅ فاز ۸: فیلدهای مورد نیاز فرانت
    business_category = serializers.CharField(
        source='business.category.name', read_only=True, default=''
    )
    business_city = serializers.CharField(
        source='business.city.name', read_only=True, default=''
    )

    class Meta:
        model = FavoriteBusiness
        fields = [
            'id', 'business', 'business_name', 'business_logo',
            'business_category', 'business_city',  # ✅ فاز ۸
            'created_at',
        ]

    def get_business_logo(self, obj):
        request = self.context.get('request')
        if obj.business.logo and request:
            return request.build_absolute_uri(obj.business.logo.url)
        return None


class FavoritePostSerializer(serializers.ModelSerializer):
    """Serializer برای علاقه‌مندی به پست"""
    # ✅ فاز ۸: فیلدهای مورد نیاز فرانت
    caption = serializers.CharField(source='post.caption', read_only=True)
    business_name = serializers.CharField(
        source='post.business.name', read_only=True
    )
    image = serializers.SerializerMethodField()

    class Meta:
        model = FavoritePost
        fields = [
            'id', 'post', 'caption', 'business_name',
            'image',  # ✅ فاز ۸
            'created_at',
        ]

    def get_image(self, obj):
        """اولین تصویر پست"""
        request = self.context.get('request')
        first_image = obj.post.images.order_by('sort_order').first()
        if first_image and request:
            return request.build_absolute_uri(first_image.image.url)
        return None


class FavoriteToggleSerializer(serializers.Serializer):
    """Serializer برای تغییر وضعیت علاقه‌مندی"""
    favorite_type = serializers.ChoiceField(
        choices=['business', 'post'],
    )
    object_id = serializers.IntegerField()