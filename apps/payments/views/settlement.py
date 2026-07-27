"""
Views برای تسویه حساب
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner, IsAdmin
from apps.core.pagination import StandardResultsSetPagination
from apps.payments.models import Settlement
from apps.payments.services.settlement_service import SettlementService
from apps.payments.serializers.settlement import (
    SettlementSerializer,
    SettlementRequestSerializer,
    BusinessFinancialStatsSerializer,
)

logger = logging.getLogger(__name__)


class BusinessFinancialStatsView(APIView, StandardResponseMixin):
    """
    آمار مالی کسب‌وکار

    GET /api/v1/payments/business/stats/
    """
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        responses={200: BusinessFinancialStatsSerializer},
        tags=['Financial'],
        summary='آمار مالی کسب‌وکار',
    )
    def get(self, request):
        business = request.user.business
        stats = SettlementService.get_business_pending_balance(business)
        serializer = BusinessFinancialStatsSerializer(stats)
        return self.success_response(data=serializer.data)


class SettlementRequestView(APIView, StandardResponseMixin):
    """
    درخواست تسویه

    POST /api/v1/payments/business/settlement/request/
    """
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        request=SettlementRequestSerializer,
        responses={201: SettlementSerializer},
        tags=['Settlement'],
        summary='درخواست تسویه',
    )
    def post(self, request):
        serializer = SettlementRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data.get('amount')

        try:
            settlement = SettlementService.request_settlement(
                business=request.user.business,
                amount=amount,
            )

            return self.success_response(
                data=SettlementSerializer(settlement).data,
                message='درخواست تسویه ثبت شد. پردازش طی ۲۴ تا ۴۸ ساعت انجام می‌شود.',
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return self.error_response(
                message=str(e),
                code='SETTLEMENT_ERROR',
            )


class SettlementListView(ListAPIView, StandardResponseMixin):
    """
    لیست تسویه‌های کسب‌وکار

    GET /api/v1/payments/business/settlements/
    """
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]
    serializer_class = SettlementSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Settlement'],
        summary='تاریخچه تسویه‌ها',
    )
    def get_queryset(self):
        return Settlement.objects.filter(
            business=self.request.user.business
        ).order_by('-requested_at')


class AdminSettlementListView(ListAPIView, StandardResponseMixin):
    """
    لیست تسویه‌های در انتظار (ادمین)

    GET /api/v1/payments/admin/settlements/pending/
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = SettlementSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Admin - Settlement'],
        summary='تسویه‌های در انتظار (ادمین)',
    )
    def get_queryset(self):
        return Settlement.objects.filter(
            status=Settlement.Status.PENDING
        ).select_related('business', 'bank_account').order_by('-requested_at')


class AdminSettlementProcessView(APIView, StandardResponseMixin):
    """
    پردازش تسویه (ادمین)

    POST /api/v1/payments/admin/settlements/<id>/process/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=['Admin - Settlement'],
        summary='پردازش تسویه',
    )
    def post(self, request, pk):
        try:
            settlement = Settlement.objects.get(id=pk)
        except Settlement.DoesNotExist:
            return self.error_response(
                message='تسویه یافت نشد',
                code='SETTLEMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        action = request.data.get('action', 'approve')

        if action == 'approve':
            success = SettlementService.process_settlement(
                settlement, admin_user=request.user
            )
            if success:
                return self.success_response(
                    data=SettlementSerializer(settlement).data,
                    message='تسویه با موفقیت پردازش شد',
                )
            else:
                return self.error_response(
                    message='خطا در پردازش تسویه',
                    code='PROCESS_ERROR',
                )

        elif action == 'reject':
            reason = request.data.get('reason', '')
            settlement.status = Settlement.Status.REJECTED
            settlement.rejection_reason = reason
            settlement.save(update_fields=['status', 'rejection_reason'])

            return self.success_response(
                data=SettlementSerializer(settlement).data,
                message='تسویه رد شد',
            )

        return self.error_response(
            message='عملیات نامعتبر',
            code='INVALID_ACTION',
        )