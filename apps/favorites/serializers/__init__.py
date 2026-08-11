"""
Serializers برای علاقه‌مندی‌ها
"""
from rest_framework import serializers
from .models import FavoriteBusiness, FavoritePost


class FavoriteBusinessSerializer(serializers.ModelSerializer):
    """Serializer برای علاقه‌مندی به کسب‌وکار"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.ImageField(source='business.logo', read_only=True)

    class Meta:
        model = FavoriteBusiness
        fields = ['id', 'business', 'business_name', 'business_logo', 'created_at']


class FavoritePostSerializer(serializers.ModelSerializer):
    """Serializer برای علاقه‌مندی به پست"""
    post_caption = serializers.CharField(source='post.caption', read_only=True)

    class Meta:
        model = FavoritePost
        fields = ['id', 'post', 'post_caption', 'created_at']


class FavoriteToggleSerializer(serializers.Serializer):
    """Serializer برای تغییر وضعیت علاقه‌مندی"""
    favorite_type = serializers.ChoiceField(
        choices=['business', 'post'],
    )
    object_id = serializers.IntegerField()