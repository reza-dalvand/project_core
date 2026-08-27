"""
Serializers لیست قیمت — نسخه نهایی
"""
from rest_framework import serializers
from apps.services.models import PriceList, PriceListNote


class PriceListNoteSerializer(serializers.ModelSerializer):
    """Serializer خواندنی یادداشت‌ها"""

    class Meta:
        model = PriceListNote
        fields = ['id', 'label', 'min_value', 'max_value']
        read_only_fields = ['id']


class PriceListNoteWriteSerializer(serializers.Serializer):
    """Serializer نوشتنی یادداشت‌ها"""
    label = serializers.CharField(max_length=100)
    min_value = serializers.IntegerField(default=0, min_value=0)
    max_value = serializers.IntegerField(default=0, min_value=0)

    # ✅ FIX فاز ۴: اعتبارسنجی max >= min
    def validate(self, data):
        min_val = data.get('min_value', 0)
        max_val = data.get('max_value', 0)
        if max_val < min_val:
            raise serializers.ValidationError(
                'مقدار حداکثر نمی‌تواند کمتر از مقدار حداقل باشد'
            )
        return data


class PriceListServiceItemSerializer(serializers.Serializer):
    """Serializer آیتم‌های خدمات در لیست قیمت"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    type_name = serializers.CharField(source='sub_service.name', default='')
    type_id = serializers.CharField(source='sub_service.type_id', default='')
    original_price = serializers.IntegerField()
    discount_percent = serializers.IntegerField()
    final_price = serializers.SerializerMethodField()
    has_deposit = serializers.BooleanField()
    deposit_amount = serializers.IntegerField()

    def get_final_price(self, obj):
        return obj.final_price


class PriceListSerializer(serializers.ModelSerializer):
    """Serializer کامل لیست قیمت"""
    notes = PriceListNoteSerializer(many=True, read_only=True)
    services = serializers.SerializerMethodField()

    class Meta:
        model = PriceList
        fields = ['id', 'theme', 'is_published', 'notes', 'services']

    def get_services(self, obj):
        services = obj.business.services.filter(is_active=True)
        return PriceListServiceItemSerializer(services, many=True).data


class PriceListUpdateSerializer(serializers.Serializer):
    """Serializer بروزرسانی لیست قیمت"""
    theme = serializers.ChoiceField(
        choices=['rose', 'gold', 'mint', 'classic'],
        required=False,
    )
    is_published = serializers.BooleanField(required=False)
    notes = PriceListNoteWriteSerializer(many=True, required=False)

    def validate_notes(self, value):
        if value is not None and len(value) > 10:
            raise serializers.ValidationError('حداکثر ۱۰ یادداشت مجاز است')
        return value

    def update(self, instance, validated_data):
        """بروزرسانی لیست قیمت با مدیریت notes"""
        notes_data = validated_data.pop('notes', None)

        # بروزرسانی فیلدهای ساده
        if 'theme' in validated_data:
            instance.theme = validated_data['theme']
        if 'is_published' in validated_data:
            instance.is_published = validated_data['is_published']
        instance.save()

        # مدیریت notes
        if notes_data is not None:
            # حذف notes قبلی و ایجاد جدید
            instance.notes.all().delete()
            for note_data in notes_data:
                PriceListNote.objects.create(
                    price_list=instance,
                    **note_data,
                )

        return instance