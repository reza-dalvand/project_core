"""
Views برای درگاه پرداخت زیبال
"""
import logging
from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.payments.models import Transaction
from apps.payments.services.zibal_service import ZibalService
from apps.payments.services.settlement_service import SettlementService
from apps.payments.serializers.payment import (
    InitiatePaymentSerializer,
    InitiatePaymentResponseSerializer,
)
from apps.bookings.models import Appointment
from apps.core.exceptions import PaymentException

logger = logging.getLogger(__name__)


class InitiatePaymentView(APIView, StandardResponseMixin):
    """
    شروع پرداخت بیعانه

    POST /api/v1/payments/initiate/
    Body: { "appointment_id": 123, "payment_method": "gateway" }
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=InitiatePaymentSerializer,
        responses={200: InitiatePaymentResponseSerializer},
        tags=['Payment'],
        summary='شروع پرداخت',
        description='شروع فرآیند پرداخت بیعانه از طریق درگاه زیبال یا کیف پول',
    )
    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment_id = serializer.validated_data['appointment_id']
        payment_method = serializer.validated_data.get('payment_method', 'gateway')

        try:
            appointment = Appointment.objects.select_related(
                'service', 'business', 'customer'
            ).get(id=appointment_id, customer=request.user)
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        # بررسی تکراری نبودن پرداخت
        if appointment.deposit_paid:
            return self.error_response(
                message='بیعانه این نوبت قبلاً پرداخت شده است',
                code='ALREADY_PAID',
            )

        deposit_amount = appointment.deposit_amount
        if deposit_amount <= 0:
            return self.error_response(
                message='این نوبت نیاز به پرداخت بیعانه ندارد',
                code='NO_DEPOSIT_REQUIRED',
            )

        # ─── پرداخت از کیف پول ───
        if payment_method == 'wallet':
            return self._pay_from_wallet(request, appointment, deposit_amount)

        # ─── پرداخت از درگاه ───
        return self._pay_from_gateway(request, appointment, deposit_amount)

    def _pay_from_wallet(self, request, appointment, amount):
        """پرداخت از کیف پول"""
        from apps.payments.services.wallet_service import WalletService

        try:
            # برداشت از کیف پول
            wallet_tx = WalletService.pay_from_wallet(
                user=request.user,
                amount=amount,
                description=f'بیعانه نوبت - {appointment.service.name}',
                reference=f'APT-{appointment.id}',
            )

            # ایجاد تراکنش
            commission, net_amount = SettlementService.calculate_net_amount(amount)

            tx = Transaction.objects.create(
                user=request.user,
                appointment=appointment,
                business=appointment.business,
                type=Transaction.Type.DEPOSIT,
                status=Transaction.Status.SUCCESS,
                amount=amount,
                original_price=appointment.original_price,
                discount_amount=appointment.original_price - appointment.final_price,
                commission_amount=commission,
                net_amount=net_amount,
                gateway=Transaction.Gateway.WALLET,
                paid_at=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            # تایید بیعانه
            SettlementService.process_deposit_payment(appointment, amount, tx)

            return self.success_response(
                data={
                    'success': True,
                    'payment_url': None,
                    'tracking_code': tx.tracking_code,
                    'transaction_id': tx.id,
                    'amount': amount,
                    'payment_method': 'wallet',
                    'message': 'پرداخت از کیف پول با موفقیت انجام شد',
                },
                message='بیعانه با موفقیت از کیف پول پرداخت شد',
            )

        except Exception as e:
            logger.error(f"Wallet payment error: {e}")
            return self.error_response(
                message=str(e),
                code='WALLET_PAYMENT_ERROR',
            )

    def _pay_from_gateway(self, request, appointment, amount):
        """پرداخت از درگاه زیبال"""
        # ایجاد تراکنش اولیه
        tx = Transaction.objects.create(
            user=request.user,
            appointment=appointment,
            business=appointment.business,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.PENDING,
            amount=amount,
            original_price=appointment.original_price,
            discount_amount=appointment.original_price - appointment.final_price,
            gateway=Transaction.Gateway.ZIBAL,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # Callback URL
        callback_url = f"{settings.SITE_DOMAIN}/api/v1/payments/callback/"

        try:
            result = ZibalService.create_payment(
                amount_toman=amount,
                callback_url=callback_url,
                description=f'بیعانه رزرو - {appointment.service.name}',
                order_id=str(tx.id),
                mobile=request.user.phone,
            )

            tx.gateway_ref_id = str(result['track_id'])
            tx.save(update_fields=['gateway_ref_id'])

            return self.success_response(
                data={
                    'success': True,
                    'payment_url': result['payment_url'],
                    'tracking_code': tx.tracking_code,
                    'transaction_id': tx.id,
                    'amount': amount,
                    'payment_method': 'gateway',
                    'message': 'لطفاً پرداخت را در درگاه بانکی تکمیل کنید',
                },
                message='لطفاً پرداخت را در درگاه بانکی تکمیل کنید',
            )

        except PaymentException as e:
            tx.status = Transaction.Status.FAILED
            tx.failure_reason = str(e)
            tx.save(update_fields=['status', 'failure_reason'])
            return e.as_response()


class PaymentCallbackView(APIView, StandardResponseMixin):
    """
    Callback درگاه پرداخت زیبال

    GET /api/v1/payments/callback/?trackId=X&success=1&orderId=Y
    """
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='trackId', type=int, required=True),
            OpenApiParameter(name='success', type=int, required=True),
            OpenApiParameter(name='orderId', type=str, required=False),
            OpenApiParameter(name='status', type=int, required=False),
        ],
        tags=['Payment'],
        summary='Callback پرداخت',
    )
    def get(self, request):
        track_id = request.query_params.get('trackId')
        success = request.query_params.get('success')
        order_id = request.query_params.get('orderId')

        if not track_id or not order_id:
            return self.error_response(
                message='پارامترهای نامعتبر',
                code='INVALID_CALLBACK',
            )

        try:
            tx = Transaction.objects.select_related(
                'appointment', 'appointment__service'
            ).get(id=order_id, gateway_ref_id=track_id)
        except Transaction.DoesNotExist:
            return self.error_response(
                message='تراکنش یافت نشد',
                code='TRANSACTION_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        # اگر قبلاً پردازش شده
        if tx.status == Transaction.Status.SUCCESS:
            return self.success_response(
                data={
                    'status': 'already_processed',
                    'appointment_id': tx.appointment_id,
                    'tracking_code': tx.tracking_code,
                },
                message='این تراکنش قبلاً پردازش شده است',
            )

        if success == '1':
            try:
                # تایید از زیبال
                result = ZibalService.verify_payment(
                    track_id=int(track_id),
                    expected_amount_toman=tx.amount,
                )

                with transaction.atomic():
                    # پردازش بیعانه
                    if tx.appointment:
                        SettlementService.process_deposit_payment(
                            tx.appointment, tx.amount, tx
                        )

                    tx.gateway_ref_id = result.get('ref_number', track_id)
                    tx.card_number = result.get('card_number', '')
                    tx.save(update_fields=['gateway_ref_id', 'card_number'])

                # هدایت به اپلیکیشن (deep link)
                deep_link = f'zibano://payment/success?tracking_code={tx.tracking_code}'
                return redirect(deep_link)

            except PaymentException as e:
                tx.status = Transaction.Status.FAILED
                tx.failure_reason = str(e)
                tx.save(update_fields=['status', 'failure_reason'])

                deep_link = f'zibano://payment/failed?tracking_code={tx.tracking_code}&reason={str(e)}'
                return redirect(deep_link)
        else:
            tx.status = Transaction.Status.FAILED
            tx.failure_reason = 'لغو توسط کاربر یا ناموفق'
            tx.save(update_fields=['status', 'failure_reason'])

            deep_link = f'zibano://payment/failed?tracking_code={tx.tracking_code}&reason=cancelled'
            return redirect(deep_link)