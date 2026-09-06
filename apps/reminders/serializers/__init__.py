from rest_framework import serializers
from apps.reminders.models import RenewalReminder

class RenewalReminderSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    
    # ✅ اضافه شدن فیلدهای مشتری
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = RenewalReminder
        fields = [
            'id',
            'business', 'business_name',
            'customer', 'customer_name', 'customer_phone', # ✅ اضافه شدند
            'service', 'service_name',
            'last_service_date', 'due_date',
            'days_remaining',
            'reminder_sent', 'sent_date',
            'has_new_booking_after_send',
            'created_at',
        ]
        read_only_fields = fields

    def get_customer_name(self, obj):
        # استخراج نام مشتری (بسته به مدل User شما)
        if hasattr(obj.customer, 'full_name') and obj.customer.full_name:
            return obj.customer.full_name
        name = f"{obj.customer.first_name} {obj.customer.last_name}".strip()
        return name or "مشتری"