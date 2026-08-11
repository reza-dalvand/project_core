"""
Views برای تاریخچه تراکنش‌ها
"""
import logging
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.payments.models import Transaction
from apps.payments.serializers.payment import (
    TransactionListSerializer,
    TransactionDetailSerializer,
)
from apps.payments.serializers.settlement import (
    TransactionFilterSerializer,
    CustomerPaymentFilterSerializer,
)
from django.db.models import Q


logger = logging.getLogger(__name__)


class CustomerPaymentHistoryView(ListAPIView, StandardResponseMixin):
    """
    تاریخچه پرداخت‌های مشتری

    GET /api/v1/payments/history/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionListSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(name='month', type=int, required=False),
            OpenApiParameter(name='year', type=int, required=False),
            OpenApiParameter(
                name='status',
                type=str,
                required=False,
                enum=['all', 'success', 'failed', 'refunded'],
            ),
        ],
        tags=['Payment History'],
        summary='تاریخچه پرداخت‌ها',
    )
    def get_queryset(self):
        qs = Transaction.objects.filter(
            user=self.request.user
        ).select_related(
            'appointment', 'appointment__service',
            'appointment__employee', 'business',
        )

        # فیلتر ماه
        month = self.request.query_params.get('month')
        if month and int(month) > 0:
            qs = qs.filter(created_at__month=int(month))

        # فیلتر سال
        year = self.request.query_params.get('year')
        if year and int(year) > 0:
            qs = qs.filter(created_at__year=int(year))

        # فیلتر وضعیت
        status_filter = self.request.query_params.get('status', 'all')
        if status_filter == 'success':
            qs = qs.filter(status=Transaction.Status.SUCCESS)
        elif status_filter == 'failed':
            qs = qs.filter(status=Transaction.Status.FAILED)
        elif status_filter == 'refunded':
            qs = qs.filter(status=Transaction.Status.REFUNDED)

        return qs.order_by('-created_at')


class CustomerTransactionDetailView(RetrieveAPIView, StandardResponseMixin):
    """
    جزئیات تراکنش مشتری

    GET /api/v1/payments/history/<id>/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionDetailSerializer

    @extend_schema(
        tags=['Payment History'],
        summary='جزئیات تراکنش',
    )
    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).select_related(
            'appointment', 'appointment__service',
            'appointment__employee', 'business',
        )


class BusinessTransactionListView(ListAPIView, StandardResponseMixin):
    """
    تراکنش‌های کسب‌وکار

    GET /api/v1/payments/business/transactions/
    """
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]
    serializer_class = TransactionListSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                required=False,
                enum=['all', 'blocked', 'settling', 'settled', 'refunded'],
            ),
            OpenApiParameter(
                name='type',
                type=str,
                required=False,
                enum=['all', 'deposit', 'full_payment', 'settlement', 'refund'],
            ),
            OpenApiParameter(name='search', type=str, required=False),
        ],
        tags=['Financial'],
        summary='تراکنش‌های کسب‌وکار',
    )
    def get_queryset(self):
        business = self.request.user.business
        qs = Transaction.objects.filter(
            business=business
        ).select_related(
            'user', 'appointment', 'appointment__service',
            'appointment__employee',
        )

        # فیلتر وضعیت
        status_filter = self.request.query_params.get('status', 'all')
        status_map = {
            'blocked': Transaction.Status.SUCCESS,
            'settling': Transaction.Status.SETTLING,
            'settled': Transaction.Status.SETTLED,
            'refunded': Transaction.Status.REFUNDED,
        }
        if status_filter in status_map:
            qs = qs.filter(status=status_map[status_filter])

        # فیلتر نوع
        type_filter = self.request.query_params.get('type', 'all')
        if type_filter != 'all':
            qs = qs.filter(type=type_filter)

        # جستجو
        search = self.request.query_params.get('search', '')
        if search:
            qs = qs.filter(
                Q(user__full_name__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(appointment__service__name__icontains=search) |
                Q(tracking_code__icontains=search)
            )

        return qs.order_by('-created_at')