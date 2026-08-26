"""
Serializers برای پشتیبانی و FAQ
"""
from rest_framework import serializers
from apps.support.models import FAQ, SupportTicket


class FAQSerializer(serializers.ModelSerializer):
    """Serializer سوالات متداول"""
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer', 'category', 'sort_order']
        read_only_fields = fields


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Serializer ایجاد تیکت"""
    class Meta:
        model = SupportTicket
        fields = ['subject', 'message', 'priority']

    def validate_subject(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('موضوع الزامی است')
        return value.strip()

    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('پیام الزامی است')
        if len(value.strip()) < 10:
            raise serializers.ValidationError('پیام باید حداقل ۱۰ کاراکتر باشد')
        return value.strip()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SupportTicketListSerializer(serializers.ModelSerializer):
    """Serializer لیست تیکت‌ها"""
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True
    )

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'message',
            'status', 'status_display',
            'priority', 'priority_display',
            'response', 'responded_at',
            'created_at',
        ]
        read_only_fields = fields


class SupportTicketDetailSerializer(SupportTicketListSerializer):
    """Serializer جزئیات تیکت"""
    class Meta(SupportTicketListSerializer.Meta):
        fields = SupportTicketListSerializer.Meta.fields