"""
Views برای پرداخت — ساده‌سازی شده
"""
import logging
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from .models import Transaction, Settlement
from .serializers import (
    TransactionListSerializer,
    TransactionDetailSerializer,
    InitiatePaymentSerializer,
    SettlementSerializer,
    SettlementRequestSerializer,
    BusinessFinancialStatsSerializer,
)
from .services.payment_service import PaymentService

logger = logging.getLogger(__name__)


class InitiatePaymentView(APIView, StandardResponseMixin):
    """شروع پرداخت بیعانه"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=InitiatePaymentSerializer,
        tags=['Payment'],
        summary='شروع پرداخت',
    )
    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment_id = serializer.validated_data['appointment_id']

        try:
            from apps.appointments.models import Appointment
            appointment = Appointment.objects.get(
                id=appointment_id,
                customer=request.user,
            )
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        if appointment.deposit_amount <= 0:
            return self.error_response(
                message='این نوبت نیاز به پرداخت بیعانه ندارد',
                code='NO_DEPOSIT_REQUIRED',
            )

        try:
            result = PaymentService.create_payment(
                appointment=appointment,
                user=request.user,
                amount=appointment.deposit_amount,
            )

            return self.success_response(
                data=result,
                message='لطفاً پرداخت را در درگاه بانکی تکمیل کنید',
            )
        except Exception as e:
            logger.error(f"Payment initiation error: {e}")
            return self.error_response(
                message=str(e),
                code='PAYMENT_ERROR',
            )


class CustomerPaymentHistoryView(generics.ListAPIView, StandardResponseMixin):
    """تاریخچه پرداخت‌های مشتری"""
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionListSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Payment History'],
        summary='تاریخچه پرداخت‌ها',
    )
    def get_queryset(self):
        return Transaction.objects.filter(
            customer=self.request.user
        ).select_related('business', 'appointment').order_by('-created_at')


class CustomerTransactionDetailView(generics.RetrieveAPIView, StandardResponseMixin):
    """جزئیات تراکنش مشتری"""
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionDetailSerializer

    @extend_schema(
        tags=['Payment History'],
        summary='جزئیات تراکنش',
    )
    def get_queryset(self):
        return Transaction.objects.filter(customer=self.request.user)


class BusinessTransactionListView(generics.ListAPIView, StandardResponseMixin):
    """تراکنش‌های کسب‌وکار"""
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]
    serializer_class = TransactionListSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Financial'],
        summary='تراکنش‌های کسب‌وکار',
    )
    def get_queryset(self):
        business = self.request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        return Transaction.objects.filter(
            business=business
        ).select_related('customer', 'appointment').order_by('-created_at')


class BusinessFinancialStatsView(APIView, StandardResponseMixin):
    """آمار مالی کسب‌وکار"""
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        responses={200: BusinessFinancialStatsSerializer},
        tags=['Financial'],
        summary='آمار مالی کسب‌وکار',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        stats = PaymentService.get_business_pending_balance(business)
        serializer = BusinessFinancialStatsSerializer(stats)
        return self.success_response(data=serializer.data)


class SettlementRequestView(APIView, StandardResponseMixin):
    """درخواست تسویه"""
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
            business = request.user.businesses.filter(
                is_active=True, status='approved'
            ).first()

            settlement = PaymentService.request_settlement(
                business=business,
                amount=amount,
            )

            return self.success_response(
                data=SettlementSerializer(settlement).data,
                message='درخواست تسویه ثبت شد.',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return self.error_response(
                message=str(e),
                code='SETTLEMENT_ERROR',
            )


class SettlementListView(generics.ListAPIView, StandardResponseMixin):
    """لیست تسویه‌های کسب‌وکار"""
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]
    serializer_class = SettlementSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Settlement'],
        summary='تاریخچه تسویه‌ها',
    )
    def get_queryset(self):
        business = self.request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        return Settlement.objects.filter(
            business=business
        ).order_by('-created_at')