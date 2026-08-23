"""
Serializers برای آگهی‌ها
"""
from rest_framework import serializers
from apps.ads.models import ModelRequest, LineRental


class ModelRequestListSerializer(serializers.ModelSerializer):
    """Serializer لیست درخواست‌های مدل + فاصله"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    business_logo = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    cost_type_display = serializers.CharField(
        source='get_cost_type_display', read_only=True
    )
    # ═══ 🆕 فاز ۳: فاصله ═══
    distance = serializers.SerializerMethodField()

    class Meta:
        model = ModelRequest
        fields = [
            'id', 'title', 'description',
            'cost_type', 'cost_type_display',
            'discount', 'is_urgent',
            'contact_phone',
            'business', 'business_name', 'business_logo',
            'service', 'service_name',
            'created_jalali', 'expires_jalali',
            'created_at',
            # ═══ 🆕 فاز ۳ ═══
            'distance',
        ]
        read_only_fields = fields

    def get_business_logo(self, obj):
        request = self.context.get('request')
        if obj.business.logo and request:
            return request.build_absolute_uri(obj.business.logo.url)
        return None

    def get_distance(self, obj):
        """
        فاصله به کیلومتر (اگر در queryset با .distance() محاسبه شده باشد)
        """
        if hasattr(obj, 'distance') and obj.distance is not None:
            # فاصله به متر است، تبدیل به کیلومتر
            return round(obj.distance.m / 1000, 2)
        return None

class ModelRequestDetailSerializer(ModelRequestListSerializer):
    """Serializer جزئیات درخواست مدل"""
    business_booking_slug = serializers.CharField(
        source='business.booking_slug', read_only=True
    )
    service_image_url = serializers.SerializerMethodField()

    class Meta(ModelRequestListSerializer.Meta):
        fields = ModelRequestListSerializer.Meta.fields + [
            'business_booking_slug', 'service_image_url',
        ]

    def get_service_image_url(self, obj):
        request = self.context.get('request')
        if obj.service_image and request:
            return request.build_absolute_uri(obj.service_image.url)
        return None


class ModelRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer ایجاد درخواست مدل"""
    class Meta:
        model = ModelRequest
        fields = [
            'service', 'title', 'description',
            'service_image', 'cost_type',
            'discount', 'is_urgent',
            'contact_phone',
        ]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('عنوان الزامی است')
        return value.strip()

    def validate_contact_phone(self, value):
        if not value or len(value) != 11:
            raise serializers.ValidationError('شماره تماس باید ۱۱ رقم باشد')
        return value

    def create(self, validated_data):
        import jdatetime

        request = self.context.get('request')
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            raise serializers.ValidationError('کسب‌وکار تایید شده یافت نشد')

        validated_data['business'] = business

        today = jdatetime.date.today()
        # ✅ اصلاح: jyear/jmonth/jday → year/month/day
        validated_data['created_jalali'] = f'{today.year}/{today.month:02d}/{today.day:02d}'

        expires = today + jdatetime.timedelta(days=30)
        # ✅ اصلاح
        validated_data['expires_jalali'] = f'{expires.year}/{expires.month:02d}/{expires.day:02d}'

        return super().create(validated_data)



class LineRentalListSerializer(serializers.ModelSerializer):
    """Serializer لیست آگهی‌های اجاره لاین + فاصله"""
    business_name = serializers.CharField(source='business.name', read_only=True)
    collab_type_display = serializers.CharField(
        source='get_collab_type_display', read_only=True
    )
    service_category_name = serializers.CharField(
        source='service_category.name', read_only=True
    )
    sub_service_name = serializers.CharField(
        source='sub_service.name', read_only=True
    )
    # ═══ 🆕 فاز ۳: فاصله ═══
    distance = serializers.SerializerMethodField()

    class Meta:
        model = LineRental
        fields = [
            'id', 'title', 'description',
            'collab_type', 'collab_type_display',
            'percent_salon', 'percent_partner',
            'fixed_amount', 'fixed_deposit', 'hourly_rate',
            'contact_phone',
            'business', 'business_name',
            'service_category', 'service_category_name',
            'sub_service', 'sub_service_name',
            'created_jalali', 'expires_jalali',
            'created_at',
            # ═══ 🆕 فاز ۳ ═══
            'distance',
        ]
        read_only_fields = fields

    def get_distance(self, obj):
        """فاصله به کیلومتر"""
        if hasattr(obj, 'distance') and obj.distance is not None:
            return round(obj.distance.m / 1000, 2)
        return None

class LineRentalDetailSerializer(LineRentalListSerializer):
    """Serializer جزئیات آگهی اجاره لاین"""
    business_booking_slug = serializers.CharField(
        source='business.booking_slug', read_only=True
    )
    line_image_url = serializers.SerializerMethodField()

    class Meta(LineRentalListSerializer.Meta):
        fields = LineRentalListSerializer.Meta.fields + [
            'business_booking_slug', 'line_image_url',
        ]

    def get_line_image_url(self, obj):
        request = self.context.get('request')
        if obj.line_image and request:
            return request.build_absolute_uri(obj.line_image.url)
        return None


class LineRentalCreateSerializer(serializers.ModelSerializer):
    """Serializer ایجاد آگهی اجاره لاین"""
    class Meta:
        model = LineRental
        fields = [
            'title', 'description', 'line_image',
            'service_category', 'sub_service',
            'collab_type',
            'percent_salon', 'percent_partner',
            'fixed_amount', 'fixed_deposit', 'hourly_rate',
            'contact_phone',
        ]

    def validate(self, data):
        collab_type = data.get('collab_type')

        if collab_type == LineRental.CollabType.PERCENT:
            if not data.get('percent_salon') or not data.get('percent_partner'):
                raise serializers.ValidationError(
                    'در نوع همکاری درصدی، درصدها الزامی هستند'
                )
            if data['percent_salon'] + data['percent_partner'] != 100:
                raise serializers.ValidationError(
                    'مجموع درصدها باید ۱۰۰٪ باشد'
                )
        elif collab_type == LineRental.CollabType.FIXED:
            if not data.get('fixed_amount'):
                raise serializers.ValidationError(
                    'در اجاره ثابت، مبلغ الزامی است'
                )
        elif collab_type == LineRental.CollabType.HOURLY:
            if not data.get('hourly_rate'):
                raise serializers.ValidationError(
                    'در اجاره ساعتی، نرخ ساعتی الزامی است'
                )

        return data

    def create(self, validated_data):
        import jdatetime
        request = self.context.get('request')
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            raise serializers.ValidationError('کسب‌وکار تایید شده یافت نشد')

        validated_data['business'] = business

        today = jdatetime.date.today()
        validated_data['created_jalali'] = f'{today.jyear}/{today.jmonth:02d}/{today.jday:02d}'
        expires = today + jdatetime.timedelta(days=30)
        validated_data['expires_jalali'] = f'{expires.jyear}/{expires.jmonth:02d}/{expires.jday:02d}'

        return super().create(validated_data)


class ModelRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer ویرایش درخواست مدل"""
    
    class Meta:
        model = ModelRequest
        fields = [
            'title', 'description', 'service_image',
            'cost_type', 'discount', 'is_urgent',
            'contact_phone',
        ]
    
    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('عنوان الزامی است')
        return value.strip()
    
    def validate_contact_phone(self, value):
        if not value or len(value) != 11:
            raise serializers.ValidationError('شماره تماس باید ۱۱ رقم باشد')
        return value


class LineRentalUpdateSerializer(serializers.ModelSerializer):
    """Serializer ویرایش آگهی اجاره لاین"""
    
    class Meta:
        model = LineRental
        fields = [
            'title', 'description', 'line_image',
            'service_category', 'sub_service',
            'collab_type',
            'percent_salon', 'percent_partner',
            'fixed_amount', 'fixed_deposit', 'hourly_rate',
            'contact_phone',
        ]
    
    def validate(self, data):
        collab_type = data.get('collab_type')
        
        if collab_type == LineRental.CollabType.PERCENT:
            if not data.get('percent_salon') or not data.get('percent_partner'):
                raise serializers.ValidationError(
                    'در نوع همکاری درصدی، درصدها الزامی هستند'
                )
            if data['percent_salon'] + data['percent_partner'] != 100:
                raise serializers.ValidationError(
                    'مجموع درصدها باید ۱۰۰٪ باشد'
                )
        elif collab_type == LineRental.CollabType.FIXED:
            if not data.get('fixed_amount'):
                raise serializers.ValidationError(
                    'در اجاره ثابت، مبلغ الزامی است'
                )
        elif collab_type == LineRental.CollabType.HOURLY:
            if not data.get('hourly_rate'):
                raise serializers.ValidationError(
                    'در اجاره ساعتی، نرخ ساعتی الزامی است'
                )
        
        return data