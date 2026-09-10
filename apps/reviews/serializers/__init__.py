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
    """Serializer برای ایجاد نظر — بدون ستاره، با رای تگ‌ها"""
    appointment_id = serializers.IntegerField()
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=300,
        default='',
    )
    tag_votes = serializers.ListField(
        child=serializers.DictField(), # [{'tag_id': 'clean', 'vote_type': 'like'}, ...]
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
        
    def validate_tag_votes(self, value):
        valid_tags = ['clean', 'punctual', 'quality', 'polite', 'fair_price', 'recommend']
        valid_types = ['like', 'dislike']
        for vote in value:
            if vote.get('tag_id') not in valid_tags:
                raise serializers.ValidationError(f"تگ {vote.get('tag_id')} نامعتبر است")
            if vote.get('vote_type') not in valid_types:
                raise serializers.ValidationError(f"نوع رای {vote.get('vote_type')} نامعتبر است")
        return value