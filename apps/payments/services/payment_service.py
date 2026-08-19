"""
Payment Service — مدیریت تراکنش‌های مالی
بدون Wallet، بدون RefundRequest
"""
import logging
from django.db import transaction
from django.db.models import Sum, Q, Case, When, Value, IntegerField
from django.utils import timezone

from apps.payments.models import Transaction, Settlement
from apps.core.utils import generate_tracking_code, generate_ref_number
from apps.core.exceptions import PaymentException

logger = logging.getLogger(__name__)



class PaymentService:
    """سرویس مدیریت تراکنش‌های مالی"""

    # ═══════════════════════════════════════════════
    #   ایجاد پرداخت
    # ═══════════════════════════════════════════════

    @classmethod
    @transaction.atomic
    def create_payment(
        cls,
        appointment,
        user,
        amount: int,
    ) -> dict:
        """
        ایجاد تراکنش پرداخت بیعانه

        Returns:
            dict: {'payment_url': str, 'tracking_code': str, ...}
        """
        if amount < 1000:
            raise PaymentException(
                message='حداقل مبلغ پرداخت ۱,۰۰۰ تومان است',
                code='MIN_AMOUNT',
            )

        # محاسبه کارمزد
        app_fee = cls.calculate_app_fee(amount)

        # ایجاد تراکنش اولیه
        tx = Transaction.objects.create(
            business=appointment.business,
            customer=user,
            appointment=appointment,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.BLOCKED,
            amount=amount,
            app_fee=app_fee,
            gateway='zibal',
        )

        # اتصال به درگاه پرداخت
        from django.conf import settings
        callback_url = f"{settings.SITE_DOMAIN}/api/v1/payments/callback/"

        try:
            from shared.payment import get_payment_gateway
            gateway = get_payment_gateway()

            result = gateway.create_payment(
                amount_toman=amount,
                callback_url=callback_url,
                description=f'بیعانه رزرو - {appointment.service.name}',
                order_id=str(tx.id),
                mobile=user.phone,
            )

            if result.success:
                tx.gateway_transaction_id = result.track_id
                tx.save(update_fields=['gateway_transaction_id'])

                return {
                    'payment_url': result.payment_url,
                    'track_id': result.track_id,
                    'tracking_code': tx.tracking_code,
                    'transaction_id': tx.id,
                    'amount': amount,
                }
            else:
                tx.status = Transaction.Status.FAILED
                tx.save(update_fields=['status'])
                raise PaymentException(
                    message=result.error_message,
                    code='GATEWAY_ERROR',
                )

        except ImportError:
            # در محیط توسعه بدون درگاه
            tx.status = Transaction.Status.FAILED
            tx.save(update_fields=['status'])
            raise PaymentException(
                message='درگاه پرداخت در دسترس نیست',
                code='GATEWAY_NOT_AVAILABLE',
            )

    # ═══════════════════════════════════════════════
    #   تایید پرداخت
    # ═══════════════════════════════════════════════

    @classmethod
    @transaction.atomic
    def verify_payment(
        cls,
        track_id: str,
        expected_amount: int,
    ) -> dict:
        """
        تایید تراکنش پرداخت پس از بازگشت از درگاه

        Returns:
            dict: {'success': bool, 'ref_number': str, ...}
        """
        try:
            tx = Transaction.objects.select_related(
                'appointment', 'appointment__service',
            ).get(gateway_transaction_id=track_id)
        except Transaction.DoesNotExist:
            raise PaymentException(
                message='تراکنش یافت نشد',
                code='TRANSACTION_NOT_FOUND',
            )

        if tx.ref_number:
            raise PaymentException(
                message='این تراکنش قبلاً تایید شده است',
                code='ALREADY_VERIFIED',
            )

        try:
            from shared.payment import get_payment_gateway
            gateway = get_payment_gateway()

            result = gateway.verify_payment(
                track_id=track_id,
                amount_toman=expected_amount,
            )

            if result.success:
                # تایید بیعانه
                cls._confirm_deposit_payment(tx, result)

                return {
                    'success': True,
                    'ref_number': result.ref_number,
                    'card_number': result.card_number,
                    'tracking_code': tx.tracking_code,
                }
            else:
                tx.status = Transaction.Status.FAILED
                tx.save(update_fields=['status'])
                raise PaymentException(
                    message=result.error_message,
                    code='VERIFY_FAILED',
                )

        except ImportError:
            raise PaymentException(
                message='درگاه پرداخت در دسترس نیست',
                code='GATEWAY_NOT_AVAILABLE',
            )

    @classmethod
    def _confirm_deposit_payment(cls, tx: Transaction, result):
        """تایید پرداخت بیعانه و فعال‌سازی نوبت"""
        tx.status = Transaction.Status.BLOCKED
        tx.ref_number = result.ref_number
        tx.card_number = result.card_number
        tx.save(update_fields=['status', 'ref_number', 'card_number'])

        # ارسال نوتیفیکیشن
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_booking_confirmed(tx.appointment)
        except Exception as e:
            logger.error(f"Failed to send booking confirmed notification: {e}")

    # ═══════════════════════════════════════════════
    #   استرداد وجه
    # ═══════════════════════════════════════════════

    @classmethod
    @transaction.atomic
    def process_refund(
        cls,
        appointment,
        refund_amount: int,
        reason: str = '',
    ):
        """
        پردازش استرداد وجه

        Args:
            appointment: نوبت مربوطه
            refund_amount: مبلغ استرداد
            reason: دلیل استرداد
        """
        if refund_amount <= 0:
            return

        # بررسی تراکنش اصلی
        tx = Transaction.objects.filter(
            appointment=appointment,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.BLOCKED,
        ).first()

        if not tx:
            logger.warning(
                f"No deposit transaction found for appointment {appointment.id}"
            )
            return

        # ایجاد تراکنش استرداد
        refund_tx = Transaction.objects.create(
            business=appointment.business,
            customer=appointment.customer,
            appointment=appointment,
            type=Transaction.Type.REFUND,
            status=Transaction.Status.REFUNDED,
            amount=refund_amount,
            refund_reason=reason,
        )

        # تغییر وضعیت تراکنش اصلی
        tx.status = Transaction.Status.REFUNDED
        tx.refund_reason = reason
        tx.save(update_fields=['status', 'refund_reason'])

        # ارسال نوتیفیکیشن
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_payment_refunded(tx, refund_amount)
        except Exception as e:
            logger.error(f"Failed to send refund notification: {e}")

        logger.info(
            f"Refund processed: appointment={appointment.id}, "
            f"amount={refund_amount}, reason={reason}"
        )

    # ═══════════════════════════════════════════════
    #   تسویه حساب
    # ═══════════════════════════════════════════════

# apps/payments/services/payment_service.py
# در کلاس PaymentService، این متد را جایگزین کنید:

    @classmethod
    def calculate_app_fee(cls, amount: int) -> int:
        """
        محاسبه کارمزد بیو کلاب — هماهنگ با فرانت‌اند
        
        قوانین:
        - زیر ۲۵۰,۰۰۰ تومان: ۷,۰۰۰ تومان ثابت
        - از ۲۵۰,۰۰۰ تا ۵۰۰,۰۰۰ تومان: ۳٪
        - از ۵۰۰,۰۰۰ تومان به بالا: ۴٪
        - سقف: ۵۰,۰۰۰ تومان
        """
        if not amount or amount <= 0:
            return 0
        
        if amount < 250000:
            fee = 7000
        elif amount <= 500000:
            fee = int(amount * 0.03)
        else:
            fee = int(amount * 0.04)
        
        return min(fee, 50000)

    @classmethod
    def get_business_pending_balance(cls, business) -> dict:
        """
        محاسبه مانده‌های مالی کسب‌وکار
        فقط ۱ کوئری با Conditional Aggregation
        """
        txs = Transaction.objects.filter(
            business=business,
            type__in=[Transaction.Type.DEPOSIT, Transaction.Type.FULL_PAYMENT],
        )

        aggregates = txs.aggregate(
            blocked=Sum(
                Case(
                    When(status=Transaction.Status.BLOCKED, then='amount'),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            settling=Sum(
                Case(
                    When(status=Transaction.Status.SETTLING, then='amount'),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            settled=Sum(
                Case(
                    When(status=Transaction.Status.SETTLED, then='amount'),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            refunded=Sum(
                Case(
                    When(status=Transaction.Status.REFUNDED, then='amount'),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            total=Sum('amount'),
        )

        return {
            'blocked': aggregates['blocked'] or 0,
            'settling': aggregates['settling'] or 0,
            'settled': aggregates['settled'] or 0,
            'refunded': aggregates['refunded'] or 0,
            'total': aggregates['total'] or 0,
        }

    @classmethod
    @transaction.atomic
    def request_settlement(cls, business, amount: int = None) -> Settlement:
        """ثبت درخواست تسویه توسط صاحب کسب‌وکار"""
        # بررسی اطلاعات بانکی
        if not business.bank_info_verified:
            raise PaymentException(
                message='اطلاعات بانکی شما هنوز تایید نشده است',
                code='BANK_NOT_VERIFIED',
            )

        balances = cls.get_business_pending_balance(business)
        available = balances['settling']

        if available <= 0:
            raise PaymentException(
                message='موجودی قابل تسویه‌ای وجود ندارد',
                code='NO_AVAILABLE_BALANCE',
            )

        if amount is None:
            amount = available
        elif amount > available:
            raise PaymentException(
                message=f'مبلغ درخواستی بیشتر از موجودی قابل تسویه است (موجودی: {available:,} تومان)',
                code='INSUFFICIENT_SETTLEMENT_BALANCE',
            )

        # بررسی عدم وجود تسویه در حال پردازش
        pending = Settlement.objects.filter(
            business=business,
            status__in=[Settlement.Status.PENDING, Settlement.Status.PROCESSING],
        ).exists()

        if pending:
            raise PaymentException(
                message='شما یک درخواست تسویه در حال پردازش دارید',
                code='PENDING_SETTLEMENT_EXISTS',
            )

        settlement = Settlement.objects.create(
            business=business,
            amount=amount,
            bank_sheba=business.bank_sheba,
            bank_name=business.bank_name,
        )

        logger.info(
            f"Settlement requested: business={business.id}, amount={amount}"
        )

        return settlement

    @classmethod
    @transaction.atomic
    def process_settlement(cls, settlement: Settlement, admin_user=None) -> bool:
        """پردازش تسویه توسط ادمین"""
        if settlement.status != Settlement.Status.PENDING:
            raise PaymentException(
                message='این تسویه قابل پردازش نیست',
                code='INVALID_SETTLEMENT_STATUS',
            )

        settlement.status = Settlement.Status.PROCESSING
        settlement.save(update_fields=['status'])

        # در آینده: اتصال به API بانکی برای واریز
        # فعلاً فقط وضعیت را تغییر می‌دهیم

        settlement.status = Settlement.Status.COMPLETED
        settlement.settled_at = timezone.now()
        settlement.save(update_fields=['status', 'settled_at'])

        # بروزرسانی تراکنش‌ها
        Transaction.objects.filter(
            business=settlement.business,
            status=Transaction.Status.SETTLING,
        ).update(
            status=Transaction.Status.SETTLED,
            settled_at=timezone.now(),
        )

        logger.info(
            f"Settlement completed: id={settlement.id}, amount={settlement.amount}"
        )

        return True