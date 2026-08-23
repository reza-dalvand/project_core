"""
Serializers مربوط به احراز هویت — بدون role
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
    expires_in = serializers.IntegerField()
    resend_after = serializers.IntegerField()
    is_registered = serializers.BooleanField()  # ✅ جدید

# ═══════════════════════════════════════════════
#   Verify OTP
# ═══════════════════════════════════════════════

class VerifyOTPSerializer(serializers.Serializer):
    """Serializer تایید کد OTP"""
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=5, min_length=5)

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


# apps/accounts/serializers/auth.py
# جایگزین کلاس‌های UserProfileSerializer و UpdateProfileSerializer

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer پروفایل کاربر — نسخه نهایی هماهنگ با فرانت
    فیلدها طوری طراحی شده‌اند که response-normalizer فرانت
    آن‌ها را به camelCase تبدیل کند:
      phone_display → phoneDisplay
      full_name → fullName
      is_national_id_verified → isNationalIdVerified
      verified_name → verifiedName
      date_joined → dateJoined
    """
    phone_display = serializers.SerializerMethodField()
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'phone',
            'phone_display',
            'first_name',
            'last_name',
            'full_name',
            'avatar',
            'is_verified',
            'is_national_id_verified',
            'verified_name',
            'date_joined',
        ]
        read_only_fields = [
            'id', 'phone', 'is_verified',
            'is_national_id_verified', 'verified_name', 'date_joined',
        ]

    def get_phone_display(self, obj):
        return mask_phone(obj.phone)



class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer بروزرسانی پروفایل"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'avatar']

    def validate_first_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError('نام باید حداقل ۲ کاراکتر باشد')
        return value.strip() if value else value

    def validate_last_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError('نام خانوادگی باید حداقل ۲ کاراکتر باشد')
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
            if User.objects.filter(phone=normalized).exists():
                raise serializers.ValidationError('این شماره قبلاً ثبت شده است')
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
    code = serializers.CharField(max_length=5, min_length=5)


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
#   Devices
# ═══════════════════════════════════════════════

class UserDeviceSerializer(serializers.Serializer):
    """Serializer دستگاه‌های فعال"""
    id = serializers.IntegerField(read_only=True)
    device_type = serializers.CharField()
    device_name = serializers.CharField()
    os_info = serializers.CharField()
    ip_address = serializers.CharField()
    location = serializers.CharField()
    is_current = serializers.BooleanField()
    last_active = serializers.DateTimeField()


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
    confirmation_code = serializers.CharField(max_length=5)


# ═══════════════════════════════════════════════
#   Custom Token Refresh
# ═══════════════════════════════════════════════

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """Token Refresh با چرخش توکن + بررسی is_active"""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['token_type'] = 'Bearer'

        try:
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(data['access'])
            user_id = access_token.get('user_id')

            # ✅ FIX فاز ۳: بررسی is_active هنگام refresh
            if user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(id=user_id)
                    if not user.is_active:
                        raise serializers.ValidationError(
                            'حساب کاربری غیرفعال شده است'
                        )
                    data['user'] = {
                        'id': user.id,
                        'is_verified': user.is_verified,
                    }
                except User.DoesNotExist:
                    raise serializers.ValidationError(
                        'کاربر یافت نشد'
                    )
        except Exception:
            pass

        return data