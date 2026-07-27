"""
Serializers برای نظرات و امتیازات
"""
from rest_framework import serializers
from apps.reviews.models import Review, ReviewResponse, ReviewTag
from apps.accounts.serializers.auth import UserProfileSerializer


class ReviewTagSerializer(serializers.ModelSerializer):
    """Serializer برای تگ‌های نظر"""

    class Meta:
        model = ReviewTag
        fields = ['id', 'label', 'icon', 'is_active']


class ReviewResponseSerializer(serializers.ModelSerializer):
    """Serializer برای پاسخ کسب‌وکار"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.ImageField(source='business.logo', read_only=True)

    class Meta:
        model = ReviewResponse
        fields = [
            'id', 'text', 'business_name', 'business_logo',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReviewListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست نظرات"""
    customer = UserProfileSerializer(read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    tags = ReviewTagSerializer(many=True, read_only=True)
    response = ReviewResponseSerializer(read_only=True)
    has_response = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'customer', 'rating', 'comment',
            'service_name', 'tags', 'response', 'has_response',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_has_response(self, obj):
        return hasattr(obj, 'response') and obj.response is not None


class ReviewDetailSerializer(ReviewListSerializer):
    """Serializer برای جزئیات نظر"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.ImageField(source='business.logo', read_only=True)

    class Meta(ReviewListSerializer.Meta):
        fields = ReviewListSerializer.Meta.fields + [
            'business_name', 'business_logo',
        ]


class CreateReviewSerializer(serializers.Serializer):
    """Serializer برای ایجاد نظر"""
    appointment_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        default='',
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    def validate_appointment_id(self, value):
        from apps.bookings.models import Appointment

        try:
            appointment = Appointment.objects.get(id=value)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError('نوبت مورد نظر یافت نشد')

        return value

    def validate_tag_ids(self, value):
        # بررسی وجود تگ‌ها
        if value:
            from apps.reviews.models import ReviewTag
            existing_tags = ReviewTag.objects.filter(
                id__in=value,
                is_active=True,
            ).count()

            if existing_tags != len(value):
                raise serializers.ValidationError('برخی از تگ‌ها نامعتبر هستند')

        return value


class CreateReviewResponseSerializer(serializers.Serializer):
    """Serializer برای ایجاد پاسخ کسب‌وکار"""
    review_id = serializers.IntegerField()
    text = serializers.CharField(min_length=10, max_length=500)

    def validate_review_id(self, value):
        try:
            review = Review.objects.get(id=value)
        except Review.DoesNotExist:
            raise serializers.ValidationError('نظر مورد نظر یافت نشد')

        return value


class UpdateReviewResponseSerializer(serializers.Serializer):
    """Serializer برای ویرایش پاسخ کسب‌وکار"""
    text = serializers.CharField(min_length=10, max_length=500)


class ReviewStatsSerializer(serializers.Serializer):
    """Serializer برای آمار نظرات"""
    avg_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    rating_distribution = serializers.DictField()


class ReviewFilterSerializer(serializers.Serializer):
    """Serializer برای فیلتر نظرات"""
    rating = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        allow_null=True,
    )
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=50,
    )