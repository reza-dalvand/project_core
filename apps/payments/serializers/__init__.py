"""
Serializers برای تراکنش‌های پرداخت
"""
from rest_framework import serializers
from apps.payments.models import Transaction, Settlement


class TransactionListSerializer(serializers.ModelSerializer):
    """Serializer لیست تراکنش‌ها"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'tracking_code', 'ref_number',
            'type', 'type_display',
            'status', 'status_display',
            'amount', 'app_fee',
            'gateway', 'gateway_transaction_id',
            'card_number', 'card_bank',
            'settled_at', 'estimated_settlement',
            'customer_phone', 'business_name',
            'created_at',
        ]


class TransactionDetailSerializer(TransactionListSerializer):
    """Serializer جزئیات تراکنش"""
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True)

    class Meta(TransactionListSerializer.Meta):
        fields = TransactionListSerializer.Meta.fields + [
            'appointment_id', 'refund_reason',
        ]


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer شروع پرداخت"""
    appointment_id = serializers.IntegerField(required=True)
    payment_method = serializers.ChoiceField(
        choices=[('gateway', 'درگاه بانکی')],
        default='gateway',
    )


class SettlementSerializer(serializers.ModelSerializer):
    """Serializer تسویه حساب"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = Settlement
        fields = [
            'id', 'amount', 'status', 'status_display',
            'bank_sheba', 'bank_name',
            'settled_at', 'business_name',
            'created_at',
        ]


class SettlementRequestSerializer(serializers.Serializer):
    """Serializer درخواست تسویه"""
    amount = serializers.IntegerField(required=False, allow_null=True)

    def validate_amount(self, value):
        if value is not None and value < 50000:
            raise serializers.ValidationError('حداقل مبلغ تسویه ۵۰,۰۰۰ تومان است')
        return value


class BusinessFinancialStatsSerializer(serializers.Serializer):
    """Serializer آمار مالی کسب‌وکار"""
    blocked = serializers.IntegerField()
    settling = serializers.IntegerField()
    settled = serializers.IntegerField()
    refunded = serializers.IntegerField()
    total = serializers.IntegerField()
