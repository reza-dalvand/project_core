"""
Serializers ویژگی‌های پیشرفته
"""
from rest_framework import serializers
from django.utils import timezone

from apps.advanced.models import (
    SearchHistory, Favorite, ReferralCode, Referral, Report
)


# ═══════════════════════════════════════════
#   Search
# ═══════════════════════════════════════════

class SearchQuerySerializer(serializers.Serializer):
    query = serializers.CharField(
        min_length=2,
        max_length=200,
        help_text='عبارت جستجو',
    )
    category = serializers.ChoiceField(
        choices=[
            ('all', 'همه'),
            ('businesses', 'کسب‌وکارها'),
            ('services', 'خدمات'),
        ],
        default='all',
        required=False,
    )
    province_id = serializers.IntegerField(required=False)
    city_id = serializers.IntegerField(required=False)
    category_id = serializers.IntegerField(required=False)
    min_rating = serializers.FloatField(required=False, default=0)
    has_discount = serializers.BooleanField(required=False, default=False)
    limit = serializers.IntegerField(required=False, default=20, max_value=100)


class SearchHistorySerializer(serializers.ModelSerializer):
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = SearchHistory
        fields = ['id', 'query', 'result_count', 'created_at', 'created_at_display']

    def get_created_at_display(self, obj):
        diff = timezone.now() - obj.created_at
        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f'{minutes} دقیقه پیش'
            return f'{hours} ساعت پیش'
        elif diff.days < 7:
            return f'{diff.days} روز پیش'
        return obj.created_at.strftime('%Y/%m/%d')


class SuggestionSerializer(serializers.Serializer):
    suggestion = serializers.CharField()


# ═══════════════════════════════════════════
#   Favorites
# ═══════════════════════════════════════════

class FavoriteToggleSerializer(serializers.Serializer):
    favorite_type = serializers.ChoiceField(choices=Favorite.Type.choices)
    object_id = serializers.IntegerField()


class FavoriteSerializer(serializers.ModelSerializer):
    favorite_type_display = serializers.CharField(
        source='get_favorite_type_display',
        read_only=True,
    )
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = [
            'id', 'favorite_type', 'favorite_type_display',
            'object_id', 'business_id', 'title',
            'created_at', 'created_at_display',
        ]

    def get_created_at_display(self, obj):
        return obj.created_at.strftime('%Y/%m/%d')


class FavoriteCheckSerializer(serializers.Serializer):
    favorite_type = serializers.ChoiceField(choices=Favorite.Type.choices)
    object_id = serializers.IntegerField()


class FavoriteCheckResponseSerializer(serializers.Serializer):
    is_favorited = serializers.BooleanField()


# ═══════════════════════════════════════════
#   Referral
# ═══════════════════════════════════════════

class ReferralCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralCode
        fields = ['code', 'total_referrals', 'total_rewards', 'is_active']


class ReferralApplySerializer(serializers.Serializer):
    code = serializers.CharField(
        max_length=20,
        help_text='کد معرف (مثل: ZIBANO-1234ABCD)',
    )


class ReferralStatsSerializer(serializers.Serializer):
    code = serializers.CharField()
    total_referrals = serializers.IntegerField()
    completed = serializers.IntegerField()
    rewarded = serializers.IntegerField()
    pending = serializers.IntegerField()
    total_rewards = serializers.IntegerField()
    referrer_reward = serializers.IntegerField()
    referred_reward = serializers.IntegerField()


class ReferralSerializer(serializers.ModelSerializer):
    referred_phone = serializers.CharField(source='referred.phone')
    referred_name = serializers.CharField(source='referred.full_name')
    status_display = serializers.CharField(source='get_status_display')
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = [
            'id', 'referred_phone', 'referred_name',
            'status', 'status_display',
            'referrer_reward', 'referred_reward',
            'created_at', 'created_at_display',
            'completed_at', 'rewarded_at',
        ]

    def get_created_at_display(self, obj):
        return obj.created_at.strftime('%Y/%m/%d')


# ═══════════════════════════════════════════
#   Geolocation
# ═══════════════════════════════════════════

class NearbySearchSerializer(serializers.Serializer):
    latitude = serializers.FloatField(
        min_value=-90,
        max_value=90,
        help_text='عرض جغرافیایی',
    )
    longitude = serializers.FloatField(
        min_value=-180,
        max_value=180,
        help_text='طول جغرافیایی',
    )
    radius_km = serializers.FloatField(
        default=10,
        min_value=1,
        max_value=100,
        help_text='شعاع جستجو به کیلومتر',
    )
    category_id = serializers.IntegerField(required=False)
    limit = serializers.IntegerField(default=20, max_value=100)


class NearbyBusinessSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    category_name = serializers.CharField()
    city_name = serializers.CharField()
    rating_avg = serializers.FloatField()
    rating_count = serializers.IntegerField()
    distance = serializers.FloatField()
    distance_display = serializers.CharField()
    logo = serializers.URLField(allow_null=True)


# ═══════════════════════════════════════════
#   Reports
# ═══════════════════════════════════════════

class ReportRequestSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=Report.Type.choices)
    format = serializers.ChoiceField(
        choices=Report.Format.choices,
        default=Report.Format.EXCEL,
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    status = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField(required=False, allow_blank=True)
    rating = serializers.IntegerField(required=False, min_value=1, max_value=5)

    def validate(self, data):
        date_from = data.get('date_from')
        date_to = data.get('date_to')

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError({
                'date_to': 'تاریخ پایان باید بعد از تاریخ شروع باشد',
            })

        return data


class ReportSerializer(serializers.ModelSerializer):
    report_type_display = serializers.CharField(
        source='get_report_type_display',
        read_only=True,
    )
    format_display = serializers.CharField(
        source='get_format_display',
        read_only=True,
    )
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'report_type', 'report_type_display',
            'format', 'format_display',
            'file', 'file_url',
            'filters', 'records_count',
            'file_size', 'file_size_display',
            'is_ready', 'error_message',
            'created_at', 'completed_at', 'expires_at',
        ]

    def get_file_url(self, obj):
        if obj.file and obj.is_ready:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_file_size_display(self, obj):
        size = obj.file_size
        if size < 1024:
            return f'{size} بایت'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} کیلوبایت'
        else:
            return f'{size / (1024 * 1024):.1f} مگابایت'