"""
Serializers برای یادآوری تمدید
"""
from rest_framework import serializers
from apps.reminders.models import RenewalReminder


class RenewalReminderSerializer(serializers.ModelSerializer):
    """Serializer یادآوری تمدید"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = RenewalReminder
        fields = [
            'id',
            'business', 'business_name',
            'service', 'service_name',
            'last_service_date', 'due_date',
            'days_remaining',
            'reminder_sent', 'sent_date',
            'has_new_booking_after_send',
            'created_at',
        ]
        read_only_fields = fields