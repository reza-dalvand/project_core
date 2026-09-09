from rest_framework import serializers
from apps.ads_management.models import AdBanner

class AdBannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    business_slug = serializers.SerializerMethodField()
    business_id = serializers.IntegerField(source='business.id', read_only=True, allow_null=True)
    
    class Meta:
        model = AdBanner
        fields = [
            'id', 'title', 'description', 'image_url', 
            'business_id', 'business_slug', 'custom_url', 
            'badge', 'order', 'created_at',
        ]
        read_only_fields = fields

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_business_slug(self, obj):
        if obj.business:
            return obj.business.booking_slug
        return None