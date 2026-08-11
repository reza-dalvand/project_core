"""
Custom JWT Authentication
پشتیبانی از Refresh Token Rotation و Blacklisting
"""
import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import (
    InvalidToken,
    TokenError,
    AuthenticationFailed,
)
from django.conf import settings

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication سفارشی با:
    - بررسی ActiveDevice
    - بررسی Blacklisted Tokens
    - استخراج Device Info
    """

    def authenticate(self, request):
        # احراز هویت استاندارد JWT
        header = self.get_header(request)
        if header is None:
            raw_token = request.COOKIES.get(settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'))
        else:
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError as e:
            raise InvalidToken(str(e))

        # بررسی Blacklist
        try:
            from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
            jti = validated_token.get('jti')
            if jti and BlacklistedToken.objects.filter(token__jti=jti).exists():
                raise AuthenticationFailed('توکن منقضی شده است')
        except ImportError:
            pass

        # گرفتن user
        try:
            user = self.get_user(validated_token)
        except Exception:
            raise AuthenticationFailed('کاربر یافت نشد')

        if not user.is_active:
            raise AuthenticationFailed('حساب کاربری غیرفعال است')

        # بررسی ActiveDevice
        device_id = validated_token.get('device_id')
        if device_id:
            from apps.accounts.models import ActiveDevice
            try:
                device = ActiveDevice.objects.get(id=device_id, user=user)
                if not device.is_trusted:
                    raise AuthenticationFailed('این دستگاه مورد اعتماد نیست')
                # به‌روزرسانی last_active
                from apps.core.utils import get_client_ip
                device.ip_address = get_client_ip(request)
                device.save(update_fields=['ip_address', 'last_active'])
            except ActiveDevice.DoesNotExist:
                raise AuthenticationFailed('نشست منقضی شده است')

        # اضافه کردن device info به request
        request.device_id = device_id
        request.validated_token = validated_token

        return (user, validated_token)


class DeviceTokenMixin:
    """Mixin برای اضافه کردن Device ID به JWT"""

    def get_token(self, user, device_id=None, **kwargs):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        if device_id:
            refresh['device_id'] = str(device_id)
            refresh.access_token['device_id'] = str(device_id)

        # اضافه کردن role
        refresh['role'] = user.role
        refresh.access_token['role'] = user.role

        # اضافه کردن is_verified
        refresh['is_verified'] = user.is_verified
        refresh.access_token['is_verified'] = user.is_verified

        # اضافه کردن اطلاعات اضافی
        for key, value in kwargs.items():
            refresh[key] = value
            refresh.access_token[key] = value

        return refresh