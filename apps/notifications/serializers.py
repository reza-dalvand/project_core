"""
Serializers برای نوتیفیکیشن‌ها
"""
from rest_framework import serializers
from .models import Notification, SMSTemplate, SMSLog


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer اعلان‌ها"""
    type_display = serializers.CharField(
        source='get_type_display', read_only=True
    )
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'type_display',
            'title', 'body', 'data',
            'is_read', 'is_pushed',
            'created_at', 'read_at', 'time_ago',
        ]
        read_only_fields = fields

    def get_time_ago(self, obj):
        """محاسبه زمان سپری شده"""
        from django.utils import timezone
        from datetime import timedelta

        diff = timezone.now() - obj.created_at

        if diff < timedelta(minutes=1):
            return 'همین الان'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes} دقیقه پیش'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours} ساعت پیش'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days} روز پیش'
        else:
            return obj.created_at.strftime('%Y/%m/%d')


class NotificationCountSerializer(serializers.Serializer):
    """Serializer تعداد اعلان‌ها"""
    total = serializers.IntegerField()
    unread = serializers.IntegerField()
    by_type = serializers.DictField()


class MarkAsReadSerializer(serializers.Serializer):
    """Serializer علامت‌گذاری خوانده شده"""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='لیست شناسه‌ها. خالی = همه',
    )


class SMSTemplateSerializer(serializers.ModelSerializer):
    """Serializer قالب‌های پیامک"""
    type_display = serializers.CharField(
        source='get_type_display', read_only=True
    )

    class Meta:
        model = SMSTemplate
        fields = [
            'id', 'type', 'type_display',
            'name', 'provider_template_id',
            'pattern', 'variables',
            'is_active', 'created_at', 'updated_at',
        ]


class SMSLogSerializer(serializers.ModelSerializer):
    """Serializer لاگ پیامک‌ها"""
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    template_name = serializers.CharField(
        source='template.name', read_only=True, default=None
    )

    class Meta:
        model = SMSLog
        fields = [
            'id', 'phone', 'template_name',
            'message', 'status', 'status_display',
            'provider_message_id', 'error_message',
            'cost', 'sent_at', 'delivered_at',
        ]