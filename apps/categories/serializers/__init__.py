"""
Serializers برای دسته‌بندی‌ها
"""
from rest_framework import serializers
from .models import ServiceCategory, SubService, BusinessCategory


class ServiceCategorySerializer(serializers.ModelSerializer):
    """Serializer برای دسته‌بندی خدمات"""
    sub_services = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'slug', 'icon_name', 'color',
            'gradient_start', 'gradient_end', 'sort_order',
            'sub_services',
        ]

    def get_sub_services(self, obj):
        sub_services = obj.sub_services.filter(is_active=True)
        return SubServiceSerializer(sub_services, many=True).data


class SubServiceSerializer(serializers.ModelSerializer):
    """Serializer برای زیرخدمت"""

    class Meta:
        model = SubService
        fields = ['id', 'name', 'slug', 'type_id', 'category']


class BusinessCategorySerializer(serializers.ModelSerializer):
    """Serializer برای نوع کسب‌وکار"""

    class Meta:
        model = BusinessCategory
        fields = ['id', 'name', 'slug']