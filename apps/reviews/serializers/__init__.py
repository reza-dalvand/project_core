"""
Serializers برای نظرات — ساده‌سازی شده
"""
from rest_framework import serializers
from apps.reviews.models import Review

class ReviewListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست نظرات"""
    customer_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    has_reply = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'customer_name', 'rating', 'comment',
            'tags', 'service_name',
            'reply', 'replied_at', 'has_reply',
            'created_at',
        ]

    def get_customer_name(self, obj):
        return obj.customer.full_name

    def get_has_reply(self, obj):
        return bool(obj.reply)


class ReviewDetailSerializer(ReviewListSerializer):
    """Serializer برای جزئیات نظر"""
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta(ReviewListSerializer.Meta):
        fields = ReviewListSerializer.Meta.fields + [
            'business_name', 'appointment',
        ]


class CreateReviewSerializer(serializers.Serializer):
    """Serializer برای ایجاد نظر"""
    appointment_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=300,
        default='',
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )

    def validate_appointment_id(self, value):
        from apps.appointments.models import Appointment
        try:
            Appointment.objects.get(id=value)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError('نوبت مورد نظر یافت نشد')
        return value


class CreateReviewReplySerializer(serializers.Serializer):
    """Serializer برای پاسخ کسب‌وکار"""
    review_id = serializers.IntegerField()
    reply = serializers.CharField(min_length=10, max_length=300)

    def validate_review_id(self, value):
        try:
            Review.objects.get(id=value)
        except Review.DoesNotExist:
            raise serializers.ValidationError('نظر مورد نظر یافت نشد')
        return value