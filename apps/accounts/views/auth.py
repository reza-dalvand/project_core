"""
Views مربوط به احراز هویت — بدون role
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken, OutstandingToken,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.core.mixins import StandardResponseMixin
from apps.core.utils import get_client_ip, get_device_info, mask_phone
from apps.core.exceptions import OTPException, ShahkarException
from apps.accounts.models import UserDevice, OtpCode
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.shahkar_service import ShahkarService
from apps.accounts.serializers.auth import (
    SendOTPSerializer,
    SendOTPResponseSerializer,
    VerifyOTPSerializer,
    UserProfileSerializer,
    UpdateProfileSerializer,
    ChangePhoneRequestSerializer,
    ChangePhoneConfirmSerializer,
    NationalIdVerificationSerializer,
    NationalIdVerificationResponseSerializer,
    UserDeviceSerializer,
    LogoutSerializer,
    DeleteAccountSerializer,
    CustomTokenRefreshSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#   Send OTP
# ═══════════════════════════════════════════════

class SendOTPView(APIView, StandardResponseMixin):
    """ارسال کد تایید به شماره موبایل"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=SendOTPSerializer,
        responses={200: SendOTPResponseSerializer},
        tags=['Authentication'],
        summary='ارسال کد تایید',
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']

        try:
            otp = OTPService.send_otp(phone)
            return self.success_response(
                data={
                    'expires_in': 300,
                    'resend_after': 60,
                },
                message=f'کد تایید به شماره {mask_phone(phone)} ارسال شد',
            )
        except OTPException as e:
            return e.as_response()
        except Exception as e:
            logger.exception(f"Send OTP error: {e}")
            return self.error_response(
                message='خطا در ارسال کد تایید. لطفاً دوباره تلاش کنید',
                code='OTP_SEND_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ═══════════════════════════════════════════════
#   Verify OTP
# ═══════════════════════════════════════════════

class VerifyOTPView(APIView, StandardResponseMixin):
    """تایید کد OTP و ورود/ثبت‌نام"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=VerifyOTPSerializer,
        tags=['Authentication'],
        summary='تایید کد و ورود',
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']

        try:
            OTPService.verify_otp(phone, code)

            user, is_new_user = User.objects.get_or_create(
                phone=phone,
                defaults={'is_verified': True},
            )
            if not is_new_user and not user.is_verified:
                user.is_verified = True
                user.save(update_fields=['is_verified'])

            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            device_info = get_device_info(request)
            device, _ = UserDevice.objects.update_or_create(
                user=user,
                device_type=device_info['device_type'],
                device_name=device_info.get('device_name', ''),
                defaults={
                    'ip_address': get_client_ip(request),
                    'os_info': device_info.get('os_version', ''),
                    'is_current': True,
                },
            )

            # ✅ تولید JWT Token — اصلاح‌شده
            refresh = RefreshToken.for_user(user)
            refresh['user_id'] = user.id
            refresh['is_verified'] = user.is_verified

            access_token = refresh.access_token
            access_token['user_id'] = user.id
            access_token['is_verified'] = user.is_verified

            access_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']

            return self.success_response(
                data={
                    'is_new_user': is_new_user,
                    'access_token': str(access_token),
                    'refresh_token': str(refresh),
                    'token_type': 'Bearer',
                    'expires_in': int(access_lifetime.total_seconds()),
                    'user': UserProfileSerializer(user).data,
                },
                message='ورود موفقیت‌آمیز' if not is_new_user else 'ثبت‌نام و ورود موفقیت‌آمیز',
            )
        except OTPException as e:
            return e.as_response()
        except Exception as e:
            logger.exception(f"Verify OTP error: {e}")
            return self.error_response(
                message='خطا در ورود. لطفاً دوباره تلاش کنید',
                code='VERIFY_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ═══════════════════════════════════════════════
#   Token Refresh
# ═══════════════════════════════════════════════

class CustomTokenRefreshView(TokenRefreshView):
    """Refresh Token با چرخش خودکار"""
    serializer_class = CustomTokenRefreshSerializer


# ═══════════════════════════════════════════════
#   Logout
# ═══════════════════════════════════════════════

class LogoutView(APIView, StandardResponseMixin):
    """خروج از حساب کاربری"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        tags=['Authentication'],
        summary='خروج از حساب',
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        all_devices = serializer.validated_data.get('all_devices', False)
        refresh_token = serializer.validated_data.get('refresh_token')

        if all_devices:
            try:
                tokens = OutstandingToken.objects.filter(user=request.user)
                for token in tokens:
                    BlacklistedToken.objects.get_or_create(token=token)
                tokens.delete()
            except Exception as e:
                logger.warning(f"Blacklist all tokens error: {e}")

            UserDevice.objects.filter(user=request.user).update(is_current=False)
            message = 'از تمام دستگاه‌ها خارج شدید'
        else:
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    logger.warning(f"Blacklist token error: {e}")

            UserDevice.objects.filter(
                user=request.user, is_current=True
            ).update(is_current=False)
            message = 'با موفقیت خارج شدید'

        return self.success_response(message=message)


# ═══════════════════════════════════════════════
#   National ID Verification
# ═══════════════════════════════════════════════

class NationalIdVerificationView(APIView, StandardResponseMixin):
    """استعلام کد ملی از سامانه شاهکار"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=NationalIdVerificationSerializer,
        responses=NationalIdVerificationResponseSerializer,
        tags=['Authentication'],
        summary='استعلام کد ملی',
    )
    def post(self, request):
        serializer = NationalIdVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        national_id = serializer.validated_data['national_id']

        try:
            result = ShahkarService.verify(national_id, request.user.phone)

            request.user.national_id = national_id
            request.user.is_national_id_verified = True
            request.user.verified_name = result.get('verified_name', '')
            request.user.save(update_fields=[
                'national_id', 'is_national_id_verified', 'verified_name',
            ])

            return self.success_response(
                data={
                    'verified_name': result['verified_name'],
                    'national_id': national_id,
                    'phone_display': mask_phone(request.user.phone),
                },
                message='هویت شما با موفقیت تایید شد',
            )
        except ShahkarException as e:
            return e.as_response()
        except Exception as e:
            logger.exception(f"National ID verification error: {e}")
            return self.error_response(
                message='خطا در استعلام کد ملی',
                code='VERIFICATION_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ═══════════════════════════════════════════════
#   Active Devices
# ═══════════════════════════════════════════════

class UserDeviceListView(APIView, StandardResponseMixin):
    """لیست دستگاه‌های فعال"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary='لیست دستگاه‌های فعال',
    )
    def get(self, request):
        devices = UserDevice.objects.filter(
            user=request.user,
        ).order_by('-last_active')

        data = UserDeviceSerializer(devices, many=True).data
        return self.success_response(
            data=data,
            meta={'count': devices.count()},
        )


class RevokeDeviceView(APIView, StandardResponseMixin):
    """خروج از یک دستگاه خاص"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary='خروج از دستگاه',
    )
    def post(self, request, device_id):
        try:
            device = UserDevice.objects.get(id=device_id, user=request.user)

            if device.is_current:
                return self.error_response(
                    message='نمی‌توانید از دستگاه فعلی خارج شوید',
                    code='CURRENT_DEVICE',
                )

            device.delete()
            return self.success_response(
                message=f'نشست {device.device_name} بسته شد',
            )
        except UserDevice.DoesNotExist:
            return self.error_response(
                message='دستگاه یافت نشد',
                code='DEVICE_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )


# ═══════════════════════════════════════════════
#   Delete Account
# ═══════════════════════════════════════════════

class DeleteAccountView(APIView, StandardResponseMixin):
    """حذف حساب کاربری"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=DeleteAccountSerializer,
        tags=['Authentication'],
        summary='حذف حساب کاربری',
    )
    def post(self, request):
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        confirmation_code = serializer.validated_data['confirmation_code']

        try:
            OTPService.verify_otp(
                request.user.phone,
                confirmation_code,
                purpose=OtpCode.Purpose.LOGIN,
            )

            user = request.user
            phone = user.phone

            # Soft delete
            user.is_active = False
            user.phone = f'deleted_{phone}_{timezone.now().timestamp()}'
            user.first_name = ''
            user.last_name = ''
            user.avatar = None
            user.national_id = ''
            user.save()

            # Blacklist همه tokens
            try:
                tokens = OutstandingToken.objects.filter(user=user)
                for token in tokens:
                    BlacklistedToken.objects.get_or_create(token=token)
            except Exception:
                pass

            UserDevice.objects.filter(user=user).delete()

            return self.success_response(
                message='حساب کاربری شما با موفقیت حذف شد',
            )
        except OTPException as e:
            return e.as_response()
        except Exception as e:
            logger.exception(f"Delete account error: {e}")
            return self.error_response(
                message='خطا در حذف حساب کاربری',
                code='DELETE_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )