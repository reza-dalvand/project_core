"""
Views مربوط به احراز هویت
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from drf_spectacular.types import OpenApiTypes

from apps.core.mixins import StandardResponseMixin
from apps.core.utils import get_client_ip, get_device_info, mask_phone
from apps.core.exceptions import (
    OTPException,
    ShahkarException,
    ZibanoBaseException,
)
from apps.accounts.models import ActiveDevice, OTP
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.shahkar_service import ShahkarService
from apps.accounts.serializers.auth import (
    SendOTPSerializer,
    SendOTPResponseSerializer,
    VerifyOTPSerializer,
    VerifyOTPResponseSerializer,
    UserProfileSerializer,
    UpdateProfileSerializer,
    ChangePhoneRequestSerializer,
    ChangePhoneConfirmSerializer,
    NationalIdVerificationSerializer,
    NationalIdVerificationResponseSerializer,
    ActiveDeviceSerializer,
    LogoutSerializer,
    DeleteAccountSerializer,
    CustomTokenRefreshSerializer,
)
from apps.api.throttles import (
    OTPSendRateThrottle,
    OTPVerifyRateThrottle,
    ResendOTPThrottle,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#   Send OTP
# ═══════════════════════════════════════════════

class SendOTPView(APIView, StandardResponseMixin):
    """ارسال کد تایید به شماره موبایل"""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OTPSendRateThrottle]

    @extend_schema(
        request=SendOTPSerializer,
        responses={
            200: SendOTPResponseSerializer,
            400: OpenApiResponse(description='Bad Request'),
            429: OpenApiResponse(description='Too Many Requests'),
        },
        tags=['Authentication'],
        summary='ارسال کد تایید',
        description='ارسال کد تایید ۵ رقمی به شماره موبایل'
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']

        try:
            otp = OTPService.send_otp(phone)

            # ❌ حذف شد: ایجاد ActiveDevice در این مرحله منطقی نیست
            # چون هنوز کاربر احراز هویت نشده است

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
    throttle_classes = [OTPVerifyRateThrottle]

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={
            200: VerifyOTPResponseSerializer,
            400: OpenApiResponse(description='Bad Request'),
            401: OpenApiResponse(description='Invalid OTP'),
        },
        tags=['Authentication'],
        summary='تایید کد و ورود',
        description='تایید کد ۵ رقمی و دریافت Access/Refresh Token'
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']

        try:
            # بررسی OTP
            OTPService.verify_otp(phone, code)

            # پیدا کردن یا ساخت کاربر
            user, is_new_user = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'is_verified': True,
                    'role': 'customer',
                }
            )

            if not is_new_user and not user.is_verified:
                user.is_verified = True
                user.save(update_fields=['is_verified'])

            # بروزرسانی IP و last_login
            user.last_login_ip = get_client_ip(request)
            user.save(update_fields=['last_login_ip'])

            # ایجاد یا بروزرسانی ActiveDevice
            device_info = get_device_info(request)
            device, _ = ActiveDevice.objects.update_or_create(
                user=user,
                device_type=device_info['device_type'],
                device_name=device_info.get('device_name', ''),
                defaults={
                    'ip_address': get_client_ip(request),
                    'app_version': device_info.get('app_version', ''),
                    'os_version': device_info.get('os_version', ''),
                    'is_trusted': True,
                }
            )

            # تولید JWT Token
            from apps.api.authentication import DeviceTokenMixin

            class TokenGenerator(DeviceTokenMixin):
                pass

            generator = TokenGenerator()
            refresh = generator.get_token(user, device_id=device.id)

            access_token = refresh.access_token
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

@extend_schema(
    request=CustomTokenRefreshSerializer,
    tags=['Authentication'],
    summary='بازسازی توکن',
)
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
        description='خروج از نشست فعلی یا تمام دستگاه‌ها'
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        all_devices = serializer.validated_data.get('all_devices', False)
        refresh_token = serializer.validated_data.get('refresh_token')

        if all_devices:
            # خروج از تمام دستگاه‌ها
            try:
                tokens = OutstandingToken.objects.filter(user=request.user)
                for token in tokens:
                    BlacklistedToken.objects.get_or_create(token=token)
                tokens.delete()
            except Exception as e:
                logger.warning(f"Blacklist all tokens error: {e}")

            # غیرفعال کردن همه ActiveDevices
            ActiveDevice.objects.filter(user=request.user).update(is_trusted=False)

            message = 'از تمام دستگاه‌ها خارج شدید'
        else:
            # فقط نشست فعلی
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    logger.warning(f"Blacklist token error: {e}")

            # غیرفعال کردن device فعلی
            if hasattr(request, 'device_id') and request.device_id:
                try:
                    ActiveDevice.objects.filter(id=request.device_id).update(is_trusted=False)
                except Exception:
                    pass

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
        description='تطبیق کد ملی با شماره موبایل از طریق سامانه شاهکار'
    )
    def post(self, request):
        serializer = NationalIdVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        national_id = serializer.validated_data['national_id']

        try:
            result = ShahkarService.verify(national_id, request.user.phone)

            # ذخیره نتیجه
            request.user.national_id = national_id
            request.user.national_id_verified = True
            request.user.verified_name = result.get('verified_name', '')
            request.user.save(update_fields=[
                'national_id', 'national_id_verified', 'verified_name'
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

class ActiveDeviceListView(generics.ListAPIView, StandardResponseMixin):
    """لیست دستگاه‌های فعال"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ActiveDeviceSerializer

    @extend_schema(
        tags=['Authentication'],
        summary='لیست دستگاه‌های فعال',
    )
    def get_queryset(self):
        return ActiveDevice.objects.filter(
            user=self.request.user,
            is_trusted=True,
        ).order_by('-last_active')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return self.success_response(
            data=serializer.data,
            meta={'count': queryset.count()},
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
            device = ActiveDevice.objects.get(id=device_id, user=request.user)

            # بررسی اینکه device فعلی نیست
            if hasattr(request, 'device_id') and str(device.id) == str(request.device_id):
                return self.error_response(
                    message='نمی‌توانید از دستگاه فعلی خارج شوید',
                    code='CURRENT_DEVICE',
                )

            # غیرفعال کردن device
            device.is_trusted = False
            device.save(update_fields=['is_trusted'])

            # Blacklist کردن token های این دستگاه
            try:
                tokens = OutstandingToken.objects.filter(
                    user=request.user,
                )
                # در حالت ایده‌آل باید device_id در token ذخیره شده باشد
                for token in tokens:
                    BlacklistedToken.objects.get_or_create(token=token)
            except Exception as e:
                logger.warning(f"Blacklist tokens error: {e}")

            return self.success_response(
                message=f'نشست {device.device_name} بسته شد',
            )

        except ActiveDevice.DoesNotExist:
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
        description='حذف دائمی حساب کاربری و تمام اطلاعات مرتبط'
    )
    def post(self, request):
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # برای حذف حساب، یک OTP ارسال کن و کد را تایید کن
        confirmation_code = serializer.validated_data['confirmation_code']

        try:
            OTPService.verify_otp(
                request.user.phone,
                confirmation_code,
                purpose=OTP.Purpose.LOGIN
            )

            # حذف حساب
            user = request.user
            phone = user.phone

            # غیرفعال کردن به جای حذف فیزیکی (soft delete)
            user.is_active = False
            user.phone = f'deleted_{phone}_{timezone.now().timestamp()}'
            user.full_name = ''
            user.avatar = None
            user.national_id = None
            user.save()

            # Blacklist کردن همه tokens
            try:
                tokens = OutstandingToken.objects.filter(user=user)
                for token in tokens:
                    BlacklistedToken.objects.get_or_create(token=token)
            except Exception:
                pass

            # غیرفعال کردن همه devices
            ActiveDevice.objects.filter(user=user).update(is_trusted=False)

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