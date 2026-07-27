"""
Serializers برای تسویه حساب
"""
from rest_framework import serializers
from apps.payments.models import Settlement


class SettlementSerializer(serializers.ModelSerializer):
    """Serializer تسویه حساب"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    bank_name = serializers.CharField(source='bank_account.bank_name', read_only=True)
    transactions_count = serializers.SerializerMethodField()

    class Meta:
        model = Settlement
        fields = [
            'id', 'amount', 'commission_total',
            'status', 'status_display',
            'frequency', 'frequency_display',
            'bank_ref_code', 'rejection_reason',
            'business_name', 'bank_name',
            'transactions_count',
            'requested_at', 'processed_at', 'completed_at',
        ]

    def get_transactions_count(self, obj):
        return obj.transactions_included.count()


class SettlementRequestSerializer(serializers.Serializer):
    """Serializer درخواست تسویه"""
    amount = serializers.IntegerField(required=False, allow_null=True)

    def validate_amount(self, value):
        if value is not None and value < 50000:
            raise serializers.ValidationError('حداقل مبلغ تسویه ۵۰,۰۰۰ تومان است')
        return value


class BusinessFinancialStatsSerializer(serializers.Serializer):
    """Serializer آمار مالی کسب‌وکار"""
    blocked = serializers.IntegerField(help_text='بیعانه بلوکه')
    settling = serializers.IntegerField(help_text='در حال تسویه')
    settled = serializers.IntegerField(help_text='تسویه شده')
    refunded = serializers.IntegerField(help_text='مسترد شده')
    total = serializers.IntegerField(help_text='کل تراکنش‌ها')
    pending_commission = serializers.IntegerField(help_text='کارمزد در انتظار')


class TransactionFilterSerializer(serializers.Serializer):
    """Serializer فیلتر تراکنش‌ها"""
    status = serializers.ChoiceField(
        choices=[
            ('all', 'همه'),
            ('blocked', 'بلوکه'),
            ('settling', 'در حال تسویه'),
            ('settled', 'تسویه شده'),
            ('refunded', 'مسترد شده'),
        ],
        required=False,
        default='all',
    )
    type = serializers.ChoiceField(
        choices=[
            ('all', 'همه'),
            ('deposit', 'بیعانه'),
            ('full_payment', 'پرداخت کامل'),
            ('settlement', 'تسویه'),
            ('refund', 'استرداد'),
        ],
        required=False,
        default='all',
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    search = serializers.CharField(required=False, allow_blank=True)


class CustomerPaymentFilterSerializer(serializers.Serializer):
    """Serializer فیلتر پرداخت‌های مشتری"""
    month = serializers.IntegerField(required=False, default=0)
    year = serializers.IntegerField(required=False, default=0)
    status = serializers.ChoiceField(
        choices=[
            ('all', 'همه'),
            ('success', 'موفق'),
            ('failed', 'ناموفق'),
            ('refunded', 'مسترد شده'),
        ],
        required=False,
        default='all',
    )