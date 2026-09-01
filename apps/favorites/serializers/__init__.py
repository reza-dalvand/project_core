"""
Serializers برای علاقه‌مندی‌ها — نسخه نهایی
"""
from rest_framework import serializers
from apps.favorites.models import FavoriteBusiness


class FavoriteBusinessSerializer(serializers.ModelSerializer):
    """Serializer برای علاقه‌مندی به کسب‌وکار"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.SerializerMethodField()
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
            'business_category', 'business_city',
            'created_at',
        ]

    def get_business_logo(self, obj):
        request = self.context.get('request')
        if obj.business.logo and request:
            return request.build_absolute_uri(obj.business.logo.url)
        return None


# ❌ کلاس FavoritePostSerializer حذف شد


class FavoriteToggleSerializer(serializers.Serializer):
    """Serializer برای تغییر وضعیت علاقه‌مندی"""
    favorite_type = serializers.ChoiceField(
        choices=['business'],  # ✅ فقط business
    )
    object_id = serializers.IntegerField()