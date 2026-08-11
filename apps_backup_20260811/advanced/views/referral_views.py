"""
Views سیستم دعوت از دوستان
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.advanced.services.referral_service import ReferralService
from apps.advanced.serializers import (
    ReferralCodeSerializer,
    ReferralApplySerializer,
    ReferralStatsSerializer,
    ReferralSerializer,
)


class ReferralCodeView(APIView, StandardResponseMixin):
    """کد معرف کاربر"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=ReferralCodeSerializer,
        tags=['Referral'],
        summary='کد معرف من',
        description='دریافت کد معرف برای دعوت از دوستان',
    )
    def get(self, request):
        code = ReferralService.get_or_create_code(request.user)
        return self.success_response(
            data=ReferralCodeSerializer(code).data
        )


class ReferralApplyView(APIView, StandardResponseMixin):
    """اعمال کد معرف"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReferralApplySerializer,
        tags=['Referral'],
        summary='اعمال کد معرف',
        description='وارد کردن کد معرف دریافتی از دوست',
    )
    def post(self, request):
        serializer = ReferralApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = ReferralService.apply_referral_code(
            referrer_code=serializer.validated_data['code'],
            new_user=request.user,
        )

        if result['success']:
            return self.success_response(
                data=result,
                message=result['message'],
            )
        else:
            return self.error_response(
                message=result['message'],
                status=status.HTTP_400_BAD_REQUEST,
            )


class ReferralStatsView(APIView, StandardResponseMixin):
    """آمار دعوت‌ها"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=ReferralStatsSerializer,
        tags=['Referral'],
        summary='آمار دعوت‌ها',
    )
    def get(self, request):
        stats = ReferralService.get_user_stats(request.user)
        return self.success_response(data=stats)


class ReferralListView(APIView, StandardResponseMixin):
    """لیست دعوت‌ها"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            {
                'name': 'status',
                'type': str,
                'required': False,
                'enum': ['pending', 'completed', 'rewarded'],
            },
        ],
        responses=ReferralSerializer(many=True),
        tags=['Referral'],
        summary='لیست دعوت‌های من',
    )
    def get(self, request):
        status_filter = request.query_params.get('status')

        referrals = ReferralService.get_referrals_list(
            user=request.user,
            status=status_filter,
        )

        return self.success_response(
            data=ReferralSerializer(referrals, many=True).data
        )