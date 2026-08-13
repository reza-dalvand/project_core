"""
Serializers پروفایل + اطلاعات بانکی (فاز ۳)
"""
from rest_framework import serializers
from apps.accounts.models import UserBankInfo


class UserBankInfoSerializer(serializers.ModelSerializer):
    """Serializer اطلاعات بانکی کاربر"""
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserBankInfo
        fields = [
            'bank_name', 'bank_id', 'sheba',
            'card_number', 'owner_name', 'is_complete',
        ]

    def validate_sheba(self, value):
        if value:
            if not value.startswith('IR'):
                raise serializers.ValidationError('شماره شبا باید با IR شروع شود')
            if len(value) != 26:
                raise serializers.ValidationError(
                    'شماره شبا باید ۲۶ کاراکتر باشد (IR + ۲۴ رقم)'
                )
        return value

    def validate_card_number(self, value):
        if value:
            if len(value) != 16:
                raise serializers.ValidationError('شماره کارت باید ۱۶ رقم باشد')
            if not value.isdigit():
                raise serializers.ValidationError('شماره کارت فقط باید شامل ارقام باشد')
        return value


class UserBankInfoUpdateSerializer(serializers.Serializer):
    """Serializer بروزرسانی اطلاعات بانکی"""
    bank_name = serializers.CharField(max_length=100)
    bank_id = serializers.CharField(max_length=20, required=False, allow_blank=True)
    sheba = serializers.CharField(max_length=26)
    card_number = serializers.CharField(max_length=16)
    owner_name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_sheba(self, value):
        if not value.startswith('IR'):
            raise serializers.ValidationError('شماره شبا باید با IR شروع شود')
        if len(value) != 26:
            raise serializers.ValidationError(
                'شماره شبا باید ۲۶ کاراکتر باشد (IR + ۲۴ رقم)'
            )
        return value

    def validate_card_number(self, value):
        if len(value) != 16:
            raise serializers.ValidationError('شماره کارت باید ۱۶ رقم باشد')
        if not value.isdigit():
            raise serializers.ValidationError('شماره کارت فقط باید شامل ارقام باشد')
        return value