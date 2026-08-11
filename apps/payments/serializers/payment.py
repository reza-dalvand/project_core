"""
Serializers برای تراکنش‌های پرداخت
"""
from rest_framework import serializers
from apps.payments.models import Transaction
from apps.appointments.models import Appointment

class TransactionListSerializer(serializers.ModelSerializer):
    """Serializer لیست تراکنش‌ها"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    gateway_display = serializers.CharField(source='get_gateway_display', read_only=True)

    # اطلاعات نوبت
    appointment_date = serializers.DateField(source='appointment.date', read_only=True)
    appointment_time = serializers.TimeField(source='appointment.time', read_only=True)
    service_name = serializers.CharField(source='appointment.service.name', read_only=True)
    employee_name = serializers.CharField(
        source='appointment.employee.name', read_only=True, default=None
    )

    # اطلاعات کسب‌وکار
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.ImageField(source='business.logo', read_only=True)

    # اطلاعات مشتری
    customer_name = serializers.CharField(source='user.full_name', read_only=True)
    customer_phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'tracking_code', 'ref_number',
            'type', 'type_display',
            'status', 'status_display',
            'amount', 'original_price', 'discount_amount',
            'commission_amount', 'net_amount',
            'gateway', 'gateway_display',
            'gateway_ref_id', 'card_number', 'card_bank',
            'description', 'failure_reason',
            'appointment_date', 'appointment_time',
            'service_name', 'employee_name',
            'business_name', 'business_logo',
            'customer_name', 'customer_phone',
            'created_at', 'paid_at', 'settled_at', 'refunded_at',
        ]


class TransactionDetailSerializer(TransactionListSerializer):
    """Serializer جزئیات تراکنش"""
    # اطلاعات کامل‌تر
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True)
    appointment_status = serializers.CharField(
        source='appointment.status', read_only=True
    )

    class Meta(TransactionListSerializer.Meta):
        fields = TransactionListSerializer.Meta.fields + [
            'appointment_id', 'appointment_status', 'ip_address',
        ]


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer شروع پرداخت"""
    appointment_id = serializers.IntegerField(required=True)
    payment_method = serializers.ChoiceField(
        choices=[
            ('gateway', 'درگاه بانکی'),
            ('wallet', 'کیف پول'),
        ],
        default='gateway',
    )

    def validate_appointment_id(self, value):
        from apps.bookings.models import Appointment
        try:
            appointment = Appointment.objects.get(id=value)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError('نوبت مورد نظر یافت نشد')
        return value


class InitiatePaymentResponseSerializer(serializers.Serializer):
    """پاسخ شروع پرداخت"""
    success = serializers.BooleanField()
    payment_url = serializers.URLField(allow_null=True)
    tracking_code = serializers.CharField()
    transaction_id = serializers.IntegerField()
    amount = serializers.IntegerField()
    payment_method = serializers.CharField()
    message = serializers.CharField()


class PaymentCallbackSerializer(serializers.Serializer):
    """Serializer Callback زیبال"""
    trackId = serializers.IntegerField(required=True)
    success = serializers.IntegerField(required=True)
    orderId = serializers.CharField(required=False, allow_blank=True)
    status = serializers.IntegerField(required=False)