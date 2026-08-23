"""
Views مربوط به پروفایل کاربر
"""
import logging
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema

from apps.accounts.serializers.profile import UserBankInfoSerializer, UserBankInfoUpdateSerializer
from apps.core.mixins import StandardResponseMixin
from apps.core.utils import mask_phone
from apps.core.exceptions import OTPException
from apps.accounts.models import OtpCode, UserBankInfo
from apps.accounts.services.otp_service import OTPService
from apps.accounts.serializers.auth import (
    UserProfileSerializer,
    UpdateProfileSerializer,
    ChangePhoneRequestSerializer,
    ChangePhoneConfirmSerializer,
)

logger = logging.getLogger(__name__)


# apps/accounts/views/profile.py
# فقط کلاس ProfileView را پیدا و جایگزین کنید:

class ProfileView(generics.RetrieveUpdateAPIView, StandardResponseMixin):
    """مشاهده و بروزرسانی پروفایل"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UpdateProfileSerializer
        return UserProfileSerializer

    @extend_schema(tags=['Profile'], summary='مشاهده پروفایل')
    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserProfileSerializer(user)
        return self.success_response(data=serializer.data)

    @extend_schema(
        request=UpdateProfileSerializer,
        responses={200: UserProfileSerializer},  # ✅ پاسخ کامل پروفایل
        tags=['Profile'],
        summary='بروزرسانی پروفایل',
    )
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UpdateProfileSerializer(
            user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # ✅ FIX فاز ۲: بازگرداندن پروفایل کامل پس از آپدیت
        # فرانت انتظار دارد پس از PUT، آبجکت کامل user را دریافت کند
        # تا store را بدون نیاز به درخواست اضافی بروزرسانی کند
        profile_serializer = UserProfileSerializer(user)
        return self.success_response(
            data=profile_serializer.data,
            message='پروفایل با موفقیت بروزرسانی شد',
        )

    
class ChangePhoneRequestView(APIView, StandardResponseMixin):
    """درخواست تغییر شماره - ارسال OTP به شماره جدید"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ChangePhoneRequestSerializer,
        tags=['Profile'],
        summary='درخواست تغییر شماره',
    )
    def post(self, request):
        serializer = ChangePhoneRequestSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        new_phone = serializer.validated_data['new_phone']

        try:
            OTPService.send_otp(
                new_phone,
                purpose=OtpCode.Purpose.CHANGE_PHONE,
                user=request.user,
            )
            return self.success_response(
                data={
                    'new_phone': new_phone,
                    'new_phone_display': mask_phone(new_phone),
                    'expires_in': 300,
                },
                message=f'کد تایید به شماره {mask_phone(new_phone)} ارسال شد',
            )
        except OTPException as e:
            return e.as_response()


class ChangePhoneConfirmView(APIView, StandardResponseMixin):
    """تایید تغییر شماره"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ChangePhoneConfirmSerializer,
        tags=['Profile'],
        summary='تایید تغییر شماره',
    )
    def post(self, request):
        serializer = ChangePhoneConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_phone = serializer.validated_data['new_phone']
        code = serializer.validated_data['code']

        try:
            OTPService.verify_otp(
                new_phone,
                code,
                purpose=OtpCode.Purpose.CHANGE_PHONE,
            )

            user = request.user
            old_phone = user.phone
            user.phone = new_phone
            user.save(update_fields=['phone'])

            logger.info(f"Phone changed for user {user.id}: {old_phone} -> {new_phone}")

            return self.success_response(
                data=UserProfileSerializer(user).data,
                message='شماره موبایل با موفقیت تغییر یافت',
            )
        except OTPException as e:
            return e.as_response()

class UserBankInfoView(APIView, StandardResponseMixin):
    """
    دریافت و ثبت اطلاعات بانکی کاربر
    🆕 فاز ۳
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: UserBankInfoSerializer},
        tags=['Profile'],
        summary='دریافت اطلاعات بانکی',
    )
    def get(self, request):
        bank_info, _ = UserBankInfo.objects.get_or_create(user=request.user)
        serializer = UserBankInfoSerializer(bank_info)
        return self.success_response(data=serializer.data)

    @extend_schema(
        request=UserBankInfoUpdateSerializer,
        responses={200: UserBankInfoSerializer},
        tags=['Profile'],
        summary='ثبت/بروزرسانی اطلاعات بانکی',
    )
    def put(self, request):
        serializer = UserBankInfoUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bank_info, _ = UserBankInfo.objects.get_or_create(user=request.user)

        bank_info.bank_name = serializer.validated_data['bank_name']
        bank_info.bank_id = serializer.validated_data.get('bank_id', '')
        bank_info.sheba = serializer.validated_data['sheba']
        bank_info.card_number = serializer.validated_data['card_number']
        bank_info.owner_name = serializer.validated_data.get(
            'owner_name', request.user.full_name
        )
        bank_info.save()

        return self.success_response(
            data=UserBankInfoSerializer(bank_info).data,
            message='اطلاعات بانکی با موفقیت ثبت شد',
        )