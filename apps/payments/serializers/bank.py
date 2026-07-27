"""
Serializers برای حساب بانکی
"""
from rest_framework import serializers
from apps.payments.models import BankAccount
from apps.core.validators import validate_sheba, validate_card_number, validate_national_id


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer حساب بانکی"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    masked_card_number = serializers.SerializerMethodField()
    masked_sheba = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            'id', 'owner_name', 'national_id',
            'bank_name', 'sheba', 'masked_sheba',
            'card_number', 'masked_card_number',
            'account_number',
            'status', 'status_display',
            'is_active', 'rejection_reason',
            'business_name',
            'verified_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'status', 'is_active', 'rejection_reason',
            'verified_at', 'created_at', 'updated_at',
        ]

    def get_masked_card_number(self, obj):
        if obj.card_number and len(obj.card_number) >= 8:
            return f'{obj.card_number[:4]} **** **** {obj.card_number[-4:]}'
        return obj.card_number

    def get_masked_sheba(self, obj):
        if obj.sheba and len(obj.sheba) >= 10:
            return f'{obj.sheba[:6]}****{obj.sheba[-4:]}'
        return obj.sheba


class BankAccountCreateSerializer(serializers.Serializer):
    """Serializer ثبت حساب بانکی"""
    owner_name = serializers.CharField(max_length=150)
    national_id = serializers.CharField(max_length=10)
    bank_name = serializers.CharField(max_length=100)
    sheba = serializers.CharField(max_length=26)
    card_number = serializers.CharField(max_length=16)
    account_number = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')

    def validate_owner_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError('نام صاحب حساب باید حداقل ۳ کاراکتر باشد')
        return value.strip()

    def validate_national_id(self, value):
        try:
            return validate_national_id(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))

    def validate_sheba(self, value):
        try:
            return validate_sheba(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))

    def validate_card_number(self, value):
        try:
            return validate_card_number(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))

    def validate(self, data):
        request = self.context.get('request')
        user = request.user

        # بررسی اینکه صاحب حساب با صاحب کسب‌وکار یکی باشد
        if hasattr(user, 'business'):
            verified_name = user.verified_name or user.full_name
            if verified_name and data['owner_name'].strip() != verified_name.strip():
                raise serializers.ValidationError({
                    'owner_name': 'نام صاحب حساب باید دقیقاً با نام تایید شده در احراز هویت مطابقت داشته باشد'
                })

        # بررسی عدم تطابق کد ملی
        if user.national_id and data['national_id'] != user.national_id:
            raise serializers.ValidationError({
                'national_id': 'کد ملی باید با کد ملی ثبت شده در احراز هویت یکسان باشد'
            })

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        business = getattr(user, 'business', None)

        # غیرفعال کردن حساب‌های قبلی
        BankAccount.objects.filter(user=user).update(is_active=False)

        return BankAccount.objects.create(
            user=user,
            business=business,
            status=BankAccount.Status.PENDING,
            is_active=True,
            **validated_data,
        )


class BankAccountUpdateSerializer(BankAccountCreateSerializer):
    """Serializer ویرایش حساب بانکی"""

    def update(self, instance, validated_data):
        # غیرفعال کردن حساب‌های قبلی
        BankAccount.objects.filter(
            user=instance.user
        ).exclude(id=instance.id).update(is_active=False)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.status = BankAccount.Status.PENDING
        instance.is_active = True
        instance.rejection_reason = ''
        instance.verified_at = None
        instance.save()

        return instance