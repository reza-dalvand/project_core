"""
Serializers برای جستجو
"""
from rest_framework import serializers
from apps.search.models import SearchHistory


class GlobalSearchSerializer(serializers.Serializer):
    """Serializer جستجوی کلی"""
    query = serializers.CharField(min_length=2, max_length=200)
    category = serializers.ChoiceField(
        choices=['all', 'businesses', 'services'],
        default='all',
        required=False,
    )
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50, required=False)


class SearchResultBusinessSerializer(serializers.Serializer):
    """نتیجه جستجوی کسب‌وکار"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    category_name = serializers.CharField()
    city_name = serializers.CharField()
    address = serializers.CharField()
    logo = serializers.SerializerMethodField()
    rating = serializers.DecimalField(max_digits=2, decimal_places=1)
    reviews_count = serializers.IntegerField()
    is_vip = serializers.BooleanField()
    booking_slug = serializers.CharField()
    distance = serializers.FloatField(required=False, allow_null=True)

    def get_logo(self, obj):
        request = self.context.get('request')
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None


class SearchResultServiceSerializer(serializers.Serializer):
    """نتیجه جستجوی خدمت"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    business_name = serializers.CharField()
    business_id = serializers.IntegerField()
    original_price = serializers.IntegerField()
    discount_percent = serializers.IntegerField()
    final_price = serializers.IntegerField()
    duration = serializers.IntegerField()
    has_deposit = serializers.BooleanField()


class SearchSuggestionsSerializer(serializers.Serializer):
    """Serializer پیشنهادات جستجو"""
    q = serializers.CharField(min_length=2, max_length=100)


class SearchHistorySerializer(serializers.ModelSerializer):
    """Serializer تاریخچه جستجو"""
    class Meta:
        model = SearchHistory
        fields = ['id', 'query', 'result_count', 'category', 'created_at']
        read_only_fields = fields


class GlobalSearchResponseSerializer(serializers.Serializer):
    """پاسخ جستجوی کلی"""
    businesses = SearchResultBusinessSerializer(many=True)
    services = SearchResultServiceSerializer(many=True)
    total = serializers.IntegerField()
    query = serializers.CharField()