"""
Serializers مربوط به احراز هویت
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from django.contrib.auth import get_user_model

from apps.core.validators import validate_iranian_phone, validate_national_id
from apps.core.utils import normalize_phone, mask_phone

User = get_user_model()


# ═══════════════════════════════════════════════
#   Send OTP
# ═══════════════════════════════════════════════

class SendOTPSerializer(serializers.Serializer):
    """Serializer ارسال کد تایید"""
    phone = serializers.CharField(max_length=15)
    device_type = serializers.ChoiceField(
        choices=['android', 'ios', 'web'],
        required=False,
        default='android'
    )
    device_name = serializers.CharField(max_length=200, required=False, default='')
    app_version = serializers.CharField(max_length=20, required=False, default='')
    os_version = serializers.CharField(max_length=50, required=False, default='')

    def validate_phone(self, value):
        try:
            cleaned = validate_iranian_phone(value)
            return normalize_phone(cleaned)
        except Exception as e:
            raise serializers.ValidationError(str(e))


class SendOTPResponseSerializer(serializers.Serializer):
    """پاسخ ارسال OTP"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    expires_in = serializers.IntegerField(help_text='زمان انقضا به ثانیه')
    resend_after = serializers.IntegerField(help_text='زمان مجاز ارسال مجدد به ثانیه')


# ═══════════════════════════════════════════════
#   Verify OTP
# ═══════════════════════════════════════════════

class VerifyOTPSerializer(serializers.Serializer):
    """Serializer تایید کد OTP"""
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=4)

    def validate_phone(self, value):
        try:
            cleaned = validate_iranian_phone(value)
            return normalize_phone(cleaned)
        except Exception as e:
            raise serializers.ValidationError(str(e))

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('کد تایید فقط باید شامل ارقام باشد')
        return value


class VerifyOTPResponseSerializer(serializers.Serializer):
    """پاسخ تایید OTP"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    is_new_user = serializers.BooleanField()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default='Bearer')
    expires_in = serializers.IntegerField()
    user = serializers.DictField()


# ═══════════════════════════════════════════════
#   User Profile
# ═══════════════════════════════════════════════

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer پروفایل کاربر"""
    phone_display = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'phone_display', 'full_name', 'avatar',
            'role', 'role_display', 'is_verified', 'national_id_verified',
            'theme', 'notification_enabled', 'date_joined',
        ]
        read_only_fields = ['id', 'phone', 'role', 'is_verified', 'date_joined']

    def get_phone_display(self, obj):
        return mask_phone(obj.phone)


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer بروزرسانی پروفایل"""

    class Meta:
        model = User
        fields = ['full_name', 'avatar', 'theme', 'notification_enabled']

    def validate_full_name(self, value):
        if value and len(value.strip()) < 3:
            raise serializers.ValidationError('نام باید حداقل ۳ کاراکتر باشد')
        return value.strip() if value else value


# ═══════════════════════════════════════════════
#   Change Phone
# ═══════════════════════════════════════════════

class ChangePhoneRequestSerializer(serializers.Serializer):
    """درخواست تغییر شماره"""
    new_phone = serializers.CharField(max_length=15)

    def validate_new_phone(self, value):
        try:
            cleaned = validate_iranian_phone(value)
            normalized = normalize_phone(cleaned)

            # بررسی اینکه این شماره قبلاً استفاده نشده
            if User.objects.filter(phone=normalized).exists():
                raise serializers.ValidationError('این شماره قبلاً ثبت شده است')

            # بررسی تفاوت با شماره فعلی
            user = self.context.get('request').user
            if user.phone == normalized:
                raise serializers.ValidationError('شماره جدید با شماره فعلی یکسان است')

            return normalized
        except Exception as e:
            if isinstance(e, serializers.ValidationError):
                raise
            raise serializers.ValidationError(str(e))


class ChangePhoneConfirmSerializer(serializers.Serializer):
    """تایید تغییر شماره"""
    new_phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=4)


# ═══════════════════════════════════════════════
#   National ID Verification
# ═══════════════════════════════════════════════

class NationalIdVerificationSerializer(serializers.Serializer):
    """استعلام کد ملی"""
    national_id = serializers.CharField(max_length=10, min_length=10)

    def validate_national_id(self, value):
        try:
            return validate_national_id(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))


class NationalIdVerificationResponseSerializer(serializers.Serializer):
    """پاسخ استعلام کد ملی"""
    success = serializers.BooleanField()
    verified_name = serializers.CharField()
    national_id = serializers.CharField()
    phone_display = serializers.CharField()


# ═══════════════════════════════════════════════
#   Active Devices
# ═══════════════════════════════════════════════

class ActiveDeviceSerializer(serializers.Serializer):
    """Serializer دستگاه‌های فعال"""
    from apps.accounts.models import ActiveDevice

    class Meta:
        model = None  # Will be set dynamically

    id = serializers.IntegerField(read_only=True)
    device_type = serializers.CharField()
    device_type_display = serializers.SerializerMethodField()
    device_name = serializers.CharField()
    os_version = serializers.CharField()
    app_version = serializers.CharField()
    ip_address = serializers.CharField()
    location = serializers.CharField()
    is_trusted = serializers.BooleanField()
    last_active = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    is_current = serializers.SerializerMethodField()

    def get_device_type_display(self, obj):
        type_map = {
            'android': 'اندروید',
            'ios': 'آیفون',
            'web': 'وب',
        }
        return type_map.get(obj.device_type, obj.device_type)

    def get_is_current(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'device_id'):
            return str(obj.id) == str(request.device_id)
        return False


# ═══════════════════════════════════════════════
#   Logout
# ═══════════════════════════════════════════════

class LogoutSerializer(serializers.Serializer):
    """Serializer خروج از حساب"""
    refresh_token = serializers.CharField(required=False)
    all_devices = serializers.BooleanField(default=False, required=False)


# ═══════════════════════════════════════════════
#   Delete Account
# ═══════════════════════════════════════════════

class DeleteAccountSerializer(serializers.Serializer):
    """Serializer حذف حساب کاربری"""
    confirmation_code = serializers.CharField(max_length=6)


# ═══════════════════════════════════════════════
#   Custom Token Refresh
# ═══════════════════════════════════════════════

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """Token Refresh با چرخش توکن"""

    def validate(self, attrs):
        data = super().validate(attrs)

        # اضافه کردن اطلاعات اضافی
        data['token_type'] = 'Bearer'

        # بررسی user info
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(data['access'])
            data['user'] = {
                'id': access_token.get('user_id'),
                'role': access_token.get('role', ''),
                'is_verified': access_token.get('is_verified', False),
            }
        except Exception:
            pass

        return data