"""
Payment Gateway Views - ادغام زیبال با سیستم رزرو
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema
from django.db import transaction
from django.conf import settings

from apps.core.mixins import StandardResponseMixin
from apps.payments.models import Transaction
from apps.payments.services.zibal_service import ZibalService
from apps.bookings.models import Appointment
from apps.bookings.services.booking_service import BookingService
from apps.core.exceptions import PaymentException


class InitiateDepositPaymentView(APIView, StandardResponseMixin):
    """
    شروع پرداخت بیعانه

    POST /api/v1/payments/initiate-deposit/
    Body: { "appointment_id": 123 }
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'appointment_id': {'type': 'integer'},
            },
            'required': ['appointment_id'],
        },
        tags=['Payment'],
        summary='شروع پرداخت بیعانه',
    )
    def post(self, request):
        appointment_id = request.data.get('appointment_id')

        if not appointment_id:
            return self.error_response(
                message='شناسه نوبت الزامی است',
                code='APPOINTMENT_ID_REQUIRED',
            )

        try:
            appointment = Appointment.objects.select_related(
                'service', 'business'
            ).get(
                id=appointment_id,
                customer=request.user,
            )
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        if appointment.deposit_paid:
            return self.error_response(
                message='بیعانه این نوبت قبلاً پرداخت شده است',
                code='ALREADY_PAID',
            )

        if appointment.deposit_amount <= 0:
            return self.error_response(
                message='این نوبت نیاز به پرداخت بیعانه ندارد',
                code='NO_DEPOSIT_REQUIRED',
            )

        # ایجاد تراکنش
        tx = Transaction.objects.create(
            user=request.user,
            appointment=appointment,
            business=appointment.business,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.PENDING,
            amount=appointment.deposit_amount,
            original_price=appointment.original_price,
            discount_amount=appointment.original_price - appointment.final_price,
            gateway=Transaction.Gateway.ZIBAL,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # اتصال به درگاه زیبال
        callback_url = f"{settings.SITE_DOMAIN}/api/v1/payments/callback/"

        try:
            result = ZibalService.create_payment(
                amount=appointment.deposit_amount * 10,  # تبدیل به ریال
                callback_url=callback_url,
                description=f'بیعانه رزرو - {appointment.service.name}',
                order_id=str(tx.id),
                mobile=request.user.phone,
            )

            tx.gateway_ref_id = str(result['track_id'])
            tx.save(update_fields=['gateway_ref_id'])

            return self.success_response(
                data={
                    'payment_url': result['payment_url'],
                    'track_id': result['track_id'],
                    'transaction_id': tx.id,
                    'tracking_code': tx.tracking_code,
                    'amount': appointment.deposit_amount,
                },
                message='لطفاً پرداخت را در درگاه بانکی تکمیل کنید',
            )

        except PaymentException as e:
            tx.status = Transaction.Status.FAILED
            tx.failure_reason = str(e)
            tx.save()
            return e.as_response()


class PaymentCallbackView(APIView, StandardResponseMixin):
    """
    Callback درگاه پرداخت

    GET /api/v1/payments/callback/?trackId=X&success=1&orderId=Y
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
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
            ).get(
                id=order_id,
                gateway_ref_id=track_id,
            )
        except Transaction.DoesNotExist:
            return self.error_response(
                message='تراکنش یافت نشد',
                code='TRANSACTION_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        if success == '1':
            try:
                # تایید پرداخت از زیبال
                result = ZibalService.verify_payment(
                    track_id=int(track_id),
                    amount=tx.amount * 10,  # ریال
                )

                with transaction.atomic():
                    # تایید بیعانه
                    if tx.appointment:
                        BookingService.confirm_deposit_payment(
                            appointment=tx.appointment,
                            transaction_record=tx,
                        )

                    tx.gateway_ref_id = result.get('ref_number', track_id)
                    tx.card_number = result.get('card_number', '')
                    tx.save()

                return self.success_response(
                    data={
                        'status': 'success',
                        'appointment_id': tx.appointment_id,
                        'tracking_code': tx.tracking_code,
                    },
                    message='پرداخت موفقیت‌آمیز بود',
                )

            except PaymentException as e:
                tx.status = Transaction.Status.FAILED
                tx.failure_reason = str(e)
                tx.save()
                return e.as_response()

        else:
            tx.status = Transaction.Status.FAILED
            tx.failure_reason = 'لغو توسط کاربر'
            tx.save()

            return self.error_response(
                message='پرداخت ناموفق بود',
                code='PAYMENT_FAILED',
            )