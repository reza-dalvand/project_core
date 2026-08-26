"""
Serializers برای خدمات
"""
from rest_framework import serializers
from apps.categories.serializers import SubServiceSerializer
from apps.services.models import Service

# apps/services/serializers/__init__.py
# فقط کلاس ServiceListSerializer را پیدا و جایگزین کنید:

class ServiceListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست خدمات — نسخه نهایی"""
    final_price = serializers.ReadOnlyField()
    discount_amount = serializers.ReadOnlyField()
    app_fee = serializers.ReadOnlyField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_id = serializers.IntegerField(source='category.id', read_only=True)
    # ✅ اصلاح: sub_service به صورت nested کامل
    sub_service = SubServiceSerializer(read_only=True)
    sub_service_id = serializers.IntegerField(source='sub_service.id', read_only=True)
    sub_service_name = serializers.CharField(source='sub_service.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description',
            'original_price', 'discount_percent',
            'final_price', 'discount_amount', 'app_fee',
            'has_deposit', 'deposit_amount',
            'duration', 'renewal_days',
            'is_active',
            'category_id', 'category_name',
            'sub_service', 'sub_service_id', 'sub_service_name',
            'business_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

        
class ServiceDetailSerializer(ServiceListSerializer):
    """Serializer کامل برای جزئیات خدمت"""

    class Meta(ServiceListSerializer.Meta):
        fields = ServiceListSerializer.Meta.fields + [
            'category', 'sub_service', 'business',
        ]


class ServiceCreateSerializer(serializers.ModelSerializer):
    """Serializer برای ایجاد خدمت جدید"""
    category = serializers.IntegerField(write_only=True)
    sub_service = serializers.IntegerField(write_only=True)

    class Meta:
        model = Service
        fields = [
            'name', 'category', 'sub_service', 'description',
            'original_price', 'discount_percent',
            'has_deposit', 'deposit_amount',
            'duration', 'renewal_days', 'is_active',
        ]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('نام خدمت الزامی است')
        if len(value.strip()) < 3:
            raise serializers.ValidationError('نام خدمت باید حداقل ۳ کاراکتر باشد')
        return value.strip()

    def validate_original_price(self, value):
        if value < 0:
            raise serializers.ValidationError('قیمت نمی‌تواند منفی باشد')
        return value

    def validate_discount_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError('درصد تخفیف باید بین ۰ تا ۱۰۰ باشد')
        return value

    def validate(self, data):
        """
        اعتبارسنجی کامل داده‌های خدمت
        ✅ سازگار با Create (POST) و Update (PATCH/PUT)
        
        بررسی‌ها:
        1. بیعانه نباید بیشتر از قیمت نهایی باشد
        2. category و sub_service (در صورت ارسال) معتبر و فعال باشند
        3. sub_service باید با category سازگار باشد
        """
        from apps.categories.models import ServiceCategory, SubService
        
        # ═══════════════════════════════════════════════
        #   ۱. استخراج مقادیر (با fallback به instance در PATCH)
        # ═══════════════════════════════════════════════
        if self.instance:
            # ─── حالت PATCH/PUT: از instance فعلی استفاده کن ───
            original_price = data.get('original_price', self.instance.original_price)
            discount_percent = data.get('discount_percent', self.instance.discount_percent)
            deposit_amount = data.get('deposit_amount', self.instance.deposit_amount)
            has_deposit = data.get('has_deposit', self.instance.has_deposit)
            category_id = data.get('category', self.instance.category_id)
            sub_service_id = data.get('sub_service', self.instance.sub_service_id)
        else:
            # ─── حالت POST: فقط از data استفاده کن ───
            original_price = data.get('original_price', 0) or 0
            discount_percent = data.get('discount_percent', 0) or 0
            deposit_amount = data.get('deposit_amount', 0) or 0
            has_deposit = data.get('has_deposit', False)
            category_id = data.get('category')
            sub_service_id = data.get('sub_service')
        
        # ═══════════════════════════════════════════════
        #   ۲. بررسی بیعانه (Deposit)
        # ═══════════════════════════════════════════════
        if has_deposit and deposit_amount and original_price:
            discount_amount_value = int(original_price * discount_percent / 100)
            final_price = max(0, original_price - discount_amount_value)
            
            if deposit_amount > final_price:
                raise serializers.ValidationError({
                    'deposit_amount': (
                        f'مبلغ بیعانه ({deposit_amount:,} تومان) نمی‌تواند '
                        f'بیشتر از قیمت نهایی ({final_price:,} تومان) باشد'
                    )
                })
        
        # ═══════════════════════════════════════════════
        #   ۳. اعتبارسنجی Category
        # ═══════════════════════════════════════════════
        category = None
        if category_id is not None:
            try:
                category = ServiceCategory.objects.get(id=category_id)
                if not category.is_active:
                    raise serializers.ValidationError({
                        'category': 'این دسته‌بندی فعال نیست'
                    })
                # جایگزینی ID با object برای ذخیره در ORM
                data['category'] = category
            except ServiceCategory.DoesNotExist:
                raise serializers.ValidationError({
                    'category': 'دسته‌بندی یافت نشد'
                })
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    'category': 'شناسه دسته‌بندی نامعتبر است'
                })
        
        # ═══════════════════════════════════════════════
        #   ۴. اعتبارسنجی SubService
        # ═══════════════════════════════════════════════
        sub_service = None
        if sub_service_id is not None:
            try:
                sub_service = SubService.objects.get(id=sub_service_id)
                if not sub_service.is_active:
                    raise serializers.ValidationError({
                        'sub_service': 'این زیرخدمت فعال نیست'
                    })
                # جایگزینی ID با object برای ذخیره در ORM
                data['sub_service'] = sub_service
            except SubService.DoesNotExist:
                raise serializers.ValidationError({
                    'sub_service': 'زیرخدمت یافت نشد'
                })
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    'sub_service': 'شناسه زیرخدمت نامعتبر است'
                })
        
        # ═══════════════════════════════════════════════
        #   ۵. بررسی سازگاری Category و SubService
        # ═══════════════════════════════════════════════
        if category and sub_service:
            # هر دو ارسال شده‌اند — باید با هم مطابقت داشته باشند
            if sub_service.category_id != category.id:
                raise serializers.ValidationError({
                    'sub_service': (
                        f'زیرخدمت «{sub_service.name}» '
                        f'با دسته‌بندی «{category.name}» مطابقت ندارد'
                    )
                })
        elif sub_service and not category:
            # فقط sub_service تغییر کرده — باید با category فعلی سازگار باشد
            if self.instance and sub_service.category_id != self.instance.category_id:
                raise serializers.ValidationError({
                    'sub_service': (
                        f'زیرخدمت «{sub_service.name}» '
                        f'با دسته‌بندی فعلی مطابقت ندارد'
                    )
                })
        elif category and not sub_service:
            # فقط category تغییر کرده — باید sub_service فعلی با آن سازگار باشد
            if self.instance and self.instance.sub_service.category_id != category.id:
                raise serializers.ValidationError({
                    'category': (
                        f'دسته‌بندی «{category.name}» '
                        f'با زیرخدمت فعلی «{self.instance.sub_service.name}» مطابقت ندارد'
                    )
                })
        
        # ═══════════════════════════════════════════════
        #   ۶. بررسی قیمت و درصد تخفیف
        # ═══════════════════════════════════════════════
        if original_price < 0:
            raise serializers.ValidationError({
                'original_price': 'قیمت نمی‌تواند منفی باشد'
            })
        
        if discount_percent is not None:
            if not (0 <= discount_percent <= 100):
                raise serializers.ValidationError({
                    'discount_percent': 'درصد تخفیف باید بین ۰ تا ۱۰۰ باشد'
                })
        
        return data
    
class ServiceUpdateSerializer(ServiceCreateSerializer):
    """Serializer برای بروزرسانی خدمت"""

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if instance.business.owner != request.user:
            raise serializers.ValidationError('شما اجازه ویرایش این خدمت را ندارید')
        return super().update(instance, validated_data)