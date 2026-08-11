"""
Views برای کیف پول - نسخه اصلاح شده
"""
import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsCustomer
from apps.core.pagination import StandardResultsSetPagination
from apps.payments.models import Transaction, WalletTransaction
from apps.payments.services.wallet_service import WalletService
from apps.payments.services.zibal_service import ZibalService
from apps.payments.serializers.wallet import (
    WalletSerializer,
    WalletSummarySerializer,
    WalletTransactionSerializer,
    WalletChargeSerializer,
)

logger = logging.getLogger(__name__)


class WalletDetailView(APIView, StandardResponseMixin):
    """اطلاعات کیف پول"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: WalletSerializer},
        tags=['Wallet'],
        summary='اطلاعات کیف پول',
    )
    def get(self, request):
        wallet = WalletService.get_or_create_wallet(request.user)
        serializer = WalletSerializer(wallet)
        return self.success_response(data=serializer.data)


class WalletSummaryView(APIView, StandardResponseMixin):
    """خلاصه وضعیت کیف پول"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: WalletSummarySerializer},
        tags=['Wallet'],
        summary='خلاصه کیف پول',
    )
    def get(self, request):
        summary = WalletService.get_wallet_summary(request.user)
        serializer = WalletSummarySerializer(summary)
        return self.success_response(data=serializer.data)


class WalletTransactionListView(ListAPIView, StandardResponseMixin):
    """لیست تراکنش‌های کیف پول"""
    permission_classes = [IsAuthenticated]
    serializer_class = WalletTransactionSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='type',
                type=str,
                required=False,
                enum=['all', 'deposit', 'withdrawal', 'refund', 'settlement'],
            ),
        ],
        tags=['Wallet'],
        summary='تراکنش‌های کیف پول',
    )
    def get_queryset(self):
        wallet = WalletService.get_or_create_wallet(self.request.user)
        qs = WalletTransaction.objects.filter(wallet=wallet)
        tx_type = self.request.query_params.get('type', 'all')
        if tx_type != 'all':
            qs = qs.filter(type=tx_type)
        return qs.order_by('-created_at')


class WalletChargeView(APIView, StandardResponseMixin):
    """
    شارژ کیف پول
    POST /api/v1/payments/wallet/charge/
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=WalletChargeSerializer,
        tags=['Wallet'],
        summary='شارژ کیف پول',
    )
    def post(self, request):
        serializer = WalletChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        # ✅ ایجاد تراکنش شارژ کیف پول با کارمزد صفر
        tx = Transaction(
            user=request.user,
            type=Transaction.Type.WALLET_TOPUP,
            status=Transaction.Status.PENDING,
            amount=amount,
            commission_amount=0,  # ✅ شارژ کیف پول کارمزد ندارد
            net_amount=amount,    # ✅ مبلغ خالص = مبلغ کل
            gateway=Transaction.Gateway.ZIBAL,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        tx.save()

        # اتصال به درگاه
        from django.conf import settings
        callback_url = f"{settings.SITE_DOMAIN}/api/v1/payments/wallet/callback/"

        try:
            result = ZibalService.create_payment(
                amount_toman=amount,
                callback_url=callback_url,
                description='شارژ کیف پول زیبانو',
                order_id=f'WALLET-{tx.id}',
                mobile=request.user.phone,
            )

            tx.gateway_ref_id = str(result['track_id'])
            tx.save(update_fields=['gateway_ref_id'])

            return self.success_response(
                data={
                    'payment_url': result['payment_url'],
                    'tracking_code': tx.tracking_code,
                    'transaction_id': tx.id,
                    'amount': amount,
                },
                message='لطفاً پرداخت را در درگاه بانکی تکمیل کنید',
            )

        except Exception as e:
            tx.status = Transaction.Status.FAILED
            tx.failure_reason = str(e)
            tx.save(update_fields=['status', 'failure_reason'])
            return self.error_response(
                message=str(e),
                code='CHARGE_ERROR',
            )


class WalletChargeCallbackView(APIView, StandardResponseMixin):
    """Callback شارژ کیف پول"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        track_id = request.query_params.get('trackId')
        success = request.query_params.get('success')
        order_id = request.query_params.get('orderId', '')

        if not order_id.startswith('WALLET-'):
            return self.error_response(
                message='تراکنش نامعتبر',
                code='INVALID_TRANSACTION',
            )

        tx_id = order_id.replace('WALLET-', '')

        try:
            tx = Transaction.objects.get(id=tx_id, type=Transaction.Type.WALLET_TOPUP)
        except Transaction.DoesNotExist:
            return self.error_response(
                message='تراکنش یافت نشد',
                code='TRANSACTION_NOT_FOUND',
            )

        if success == '1':
            try:
                result = ZibalService.verify_payment(
                    track_id=int(track_id),
                    expected_amount_toman=tx.amount,
                )

                # شارژ کیف پول
                WalletService.deposit(
                    user=request.user,
                    amount=tx.amount,
                    description='شارژ کیف پول',
                    reference=f'TX-{tx.id}',
                )

                tx.status = Transaction.Status.SUCCESS
                tx.paid_at = timezone.now()
                tx.gateway_ref_id = result.get('ref_number', track_id)
                tx.card_number = result.get('card_number', '')
                tx.save()

                return self.success_response(
                    data={'amount': tx.amount},
                    message='کیف پول با موفقیت شارژ شد',
                )

            except Exception as e:
                tx.status = Transaction.Status.FAILED
                tx.failure_reason = str(e)
                tx.save()
                return self.error_response(message=str(e))
        else:
            tx.status = Transaction.Status.FAILED
            tx.failure_reason = 'لغو توسط کاربر'
            tx.save()
            return self.error_response(message='پرداخت ناموفق')