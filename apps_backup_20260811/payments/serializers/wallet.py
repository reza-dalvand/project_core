"""
Serializers برای کیف پول
"""
from rest_framework import serializers
from apps.payments.models import Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    """Serializer کیف پول"""
    class Meta:
        model = Wallet
        fields = [
            'id', 'balance', 'total_credit', 'total_debit',
            'is_frozen', 'updated_at',
        ]


class WalletSummarySerializer(serializers.Serializer):
    """Serializer خلاصه کیف پول"""
    balance = serializers.IntegerField()
    total_credit = serializers.IntegerField()
    total_debit = serializers.IntegerField()
    is_frozen = serializers.BooleanField()
    recent_deposits = serializers.IntegerField()
    recent_withdrawals = serializers.IntegerField()
    recent_transactions_count = serializers.IntegerField()


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer تراکنش‌های کیف پول"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'amount', 'type', 'type_display',
            'description', 'balance_after', 'reference',
            'created_at',
        ]


class WalletChargeSerializer(serializers.Serializer):
    """Serializer شارژ کیف پول"""
    amount = serializers.IntegerField(min_value=1000)
    payment_method = serializers.ChoiceField(
        choices=[('gateway', 'درگاه بانکی')],
        default='gateway',
    )

    def validate_amount(self, value):
        if value < 10000:
            raise serializers.ValidationError('حداقل مبلغ شارژ ۱۰,۰۰۰ تومان است')
        if value > 50000000:
            raise serializers.ValidationError('حداکثر مبلغ شارژ ۵۰,۰۰۰,۰۰۰ تومان است')
        return value


class WalletWithdrawSerializer(serializers.Serializer):
    """Serializer برداشت از کیف پول"""
    amount = serializers.IntegerField(min_value=10000)
    description = serializers.CharField(required=False, allow_blank=True, default='')