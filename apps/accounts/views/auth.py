"""
Views مربوط به احراز هویت — بدون role
✅ FIX F-15: اضافه شدن SessionStatusView
"""
import logging
import uuid
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
from drf_spectacular.utils import extend_schema
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
            is_registered = User.objects.filter(phone=phone).exists()

            return self.success_response(
                data={
                    'expires_in': 300,
                    'resend_after': 120,
                    'is_registered': is_registered,
                },
                message=f'کد تایید به شماره {mask_phone(phone)} ارسال شد',
            )
        except OTPException as e:
            return e.as_response()
        except Exception as e:
            logger.exception(f"Send OTP error: {e}")
            return self.error_response(
                message='خطا در ارسال کد تایید. لطفاً دوباره تلاش کنید.',
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

            if not is_new_user and not user.is_active:
                return self.error_response(
                    message='این حساب کاربری غیرفعال شده است. لطفاً با پشتیبانی تماس بگیرید.',
                    code='ACCOUNT_DEACTIVATED',
                    status=status.HTTP_403_FORBIDDEN,
                )

            is_suspended = user.is_suspended
            suspension_reason = user.suspension_reason if is_suspended else ''

            if not is_new_user and not user.is_verified:
                user.is_verified = True
                user.save(update_fields=['is_verified'])

            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            device_info = get_device_info(request)
            client_ip = get_client_ip(request)

            try:
                UserDevice.objects.update_or_create(
                    user=user,
                    device_type=device_info['device_type'],
                    defaults={
                        'device_name': device_info.get('device_name') or f'{device_info["device_type"]} Device',
                        'ip_address': client_ip or '127.0.0.1',
                        'os_info': device_info.get('os_info') or device_info.get('os_version') or 'Unknown',
                        'location': 'Unknown',
                        'is_current': True,
                    },
                )
            except Exception as device_err:
                logger.warning(f"Device registration failed: {device_err}")

            refresh = RefreshToken.for_user(user)
            refresh['user_id'] = user.id
            refresh['is_verified'] = user.is_verified
            access_token = refresh.access_token
            access_token['user_id'] = user.id
            access_token['is_verified'] = user.is_verified

            needs_profile_completion = (
                is_new_user or
                not user.first_name or
                not user.last_name
            )

            return self.success_response(
                data={
                    'is_new_user': is_new_user,
                    'needs_profile_completion': needs_profile_completion,
                    'access_token': str(access_token),
                    'refresh_token': str(refresh),
                    'token_type': 'Bearer',
                    'expires_in': int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
                    'refresh_expires_in': int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
                    'user': UserProfileSerializer(user).data,
                    'is_suspended': is_suspended,
                    'suspension_reason': suspension_reason,
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
#   ✅ FIX F-15: Session Status Check
# ═══════════════════════════════════════════════

class SessionStatusView(APIView, StandardResponseMixin):
    """
    بررسی وضعیت فعلی session کاربر
    
    این اندپوینت سبک برای بررسی:
    - وضعیت تعلیق کاربر
    - وضعیت فعال بودن حساب
    - اطلاعات ضروری پروفایل
    
    فرانت‌اند هر ۵ دقیقه یکبار (هنگام focus/visibility) این را صدا می‌زند.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary='بررسی وضعیت session',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'isSuspended': {'type': 'boolean'},
                    'suspensionReason': {'type': 'string'},
                    'isDeactivated': {'type': 'boolean'},
                    'isActive': {'type': 'boolean'},
                    'isVerified': {'type': 'boolean'},
                }
            }
        },
    )
    def get(self, request):
        user = request.user
        
        return self.success_response(
            data={
                'isSuspended': getattr(user, 'is_suspended', False),
                'suspensionReason': getattr(user, 'suspension_reason', '') or '',
                'isDeactivated': not user.is_active,
                'isActive': user.is_active,
                'isVerified': user.is_verified,
            }
        )


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
# National ID Verification
# ═══════════════════════════════════════════════

class NationalIdVerificationView(APIView, StandardResponseMixin):
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
            from shared.national_id import get_national_id_verifier
            verifier = get_national_id_verifier()
            
            result = verifier.verify(
                national_id=national_id, 
                phone=request.user.phone,
                full_name=request.user.full_name
            )

            if result.success:
                final_verified_name = request.user.full_name or result.verified_name
                
                user = request.user
                user.national_id = national_id
                user.is_national_id_verified = True
                user.verified_name = final_verified_name
                user.save(update_fields=[
                    'national_id',
                    'is_national_id_verified',
                    'verified_name',
                ])

                business = user.businesses.first()
                if business:
                    business.national_id = national_id
                    business.is_national_id_verified = True
                    business.verified_name = final_verified_name
                    business.save(update_fields=[
                        'national_id',
                        'is_national_id_verified',
                        'verified_name',
                    ])

                return self.success_response(
                    data={
                        'verified_name': final_verified_name,
                        'national_id': national_id,
                        'phone_display': mask_phone(user.phone),
                    },
                    message='هویت شما با موفقیت تایید شد',
                )
            else:
                return self.error_response(
                    message=result.error_message or 'کد ملی با شماره موبایل تطابق ندارد',
                    code=result.error_code or 'MISMATCH',
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except ValueError as e:
            logger.error(f"National ID config error: {e}")
            return self.error_response(
                message=str(e),
                code='CONFIG_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
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
                purpose=OtpCode.Purpose.DELETE_ACCOUNT,
            )

            user = request.user
            phone = user.phone

            user.is_active = False
            user.phone = f'del_{uuid.uuid4().hex[:7]}'
            user.first_name = ''
            user.last_name = ''
            user.avatar = None
            user.national_id = ''
            user.save()

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


class SendDeleteAccountOTPView(APIView, StandardResponseMixin):
    """ارسال کد تایید برای حذف حساب"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary='ارسال کد تایید حذف حساب',
    )
    def post(self, request):
        try:
            OTPService.send_otp(
                request.user.phone,
                purpose=OtpCode.Purpose.DELETE_ACCOUNT,
            )
            return self.success_response(
                data={
                    'expires_in': 300,
                    'resend_after': 60,
                },
                message=f'کد تایید حذف حساب به شماره {mask_phone(request.user.phone)} ارسال شد',
            )
        except OTPException as e:
            return e.as_response()
        except Exception as e:
            logger.exception(f"Send delete OTP error: {e}")
            return self.error_response(
                message='خطا در ارسال کد تایید',
                code='OTP_SEND_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )