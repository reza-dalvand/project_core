# apps/services/serializers/price_list.py (نسخه نهایی کامل)
from rest_framework import serializers
from apps.services.models import PriceList, PriceListNote


class PriceListNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceListNote
        fields = ['id', 'label', 'min_value', 'max_value']


class PriceListNoteWriteSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=100)
    min_value = serializers.IntegerField(default=0)
    max_value = serializers.IntegerField(default=0)


class PriceListSerializer(serializers.ModelSerializer):
    notes = PriceListNoteSerializer(many=True, read_only=True)
    services = serializers.SerializerMethodField()

    class Meta:
        model = PriceList
        fields = ['id', 'theme', 'is_published', 'notes', 'services']

    def get_services(self, obj):
        services = obj.business.services.filter(is_active=True)
        return [{
            'id': s.id,
            'name': s.name,
            'type_name': s.sub_service.name if s.sub_service else '',
            'type_id': s.sub_service.type_id if s.sub_service else '',
            'original_price': s.original_price,
            'discount_percent': s.discount_percent,
            'final_price': s.final_price,
            'has_deposit': s.has_deposit,
            'deposit_amount': s.deposit_amount,
        } for s in services]


class PriceListUpdateSerializer(serializers.Serializer):
    theme = serializers.ChoiceField(
        choices=['rose', 'gold', 'mint', 'classic'],
        required=False,
    )
    is_published = serializers.BooleanField(required=False)
    notes = PriceListNoteWriteSerializer(many=True, required=False)

    def update(self, instance, validated_data):
        notes_data = validated_data.pop('notes', None)

        if 'theme' in validated_data:
            instance.theme = validated_data['theme']
        if 'is_published' in validated_data:
            instance.is_published = validated_data['is_published']
        instance.save()

        if notes_data is not None:
            instance.notes.all().delete()
            for note_data in notes_data:
                PriceListNote.objects.create(
                    price_list=instance,
                    **note_data,
                )

        return instance