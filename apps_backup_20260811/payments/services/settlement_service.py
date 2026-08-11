"""
سرویس تسویه حساب با صاحبان کسب‌وکار
✅ بهینه‌شده: Conditional Aggregation و Prefetch
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q, Case, When, Value, IntegerField, Prefetch
from django.utils import timezone
from django.conf import settings
from apps.payments.models import (
    Transaction, Settlement, BankAccount, Wallet, WalletTransaction,
)
from apps.businesses.models import Business
from apps.core.exceptions import PaymentException

logger = logging.getLogger(__name__)


class SettlementService:
    """سرویس مدیریت تسویه حساب"""

    COMMISSION_PERCENT = Decimal('0.01')
    MIN_COMMISSION = 10000

    @classmethod
    def calculate_commission(cls, amount: int) -> int:
        """محاسبه کارمزد زیبانو"""
        commission = int(amount * cls.COMMISSION_PERCENT)
        return max(commission, cls.MIN_COMMISSION)

    @classmethod
    def calculate_net_amount(cls, amount: int) -> tuple:
        """
        محاسبه مبلغ خالص پس از کسر کارمزد
        Returns:
            tuple: (commission, net_amount)
        """
        commission = cls.calculate_commission(amount)
        net_amount = amount - commission
        return commission, net_amount

    @classmethod
    @transaction.atomic
    def process_deposit_payment(cls, appointment, amount: int, transaction_record):
        """پردازش پرداخت بیعانه"""
        commission, net_amount = cls.calculate_net_amount(amount)
        transaction_record.commission_amount = commission
        transaction_record.net_amount = net_amount
        transaction_record.status = Transaction.Status.SUCCESS
        transaction_record.paid_at = timezone.now()
        transaction_record.save()

        appointment.deposit_paid = True
        appointment.status = appointment.Status.CONFIRMED
        appointment.save(update_fields=['deposit_paid', 'status', 'updated_at'])

        logger.info(
            f"Deposit processed: appointment={appointment.id}, "
            f"amount={amount}, commission={commission}, net={net_amount}"
        )

    @classmethod
    @transaction.atomic
    def release_deposit(cls, appointment, transaction_record):
        """آزادسازی بیعانه پس از تایید خدمت"""
        business = appointment.business
        owner = business.owner

        if not transaction_record or transaction_record.status != Transaction.Status.SUCCESS:
            raise PaymentException(
                message='تراکنش بیعانه یافت نشد یا ناموفق است',
                code='INVALID_TRANSACTION',
            )

        if transaction_record.settled_at:
            raise PaymentException(
                message='این تراکنش قبلاً تسویه شده است',
                code='ALREADY_SETTLED',
            )

        net_amount = transaction_record.net_amount

        try:
            bank_account = BankAccount.objects.get(
                business=business,
                status=BankAccount.Status.VERIFIED,
                is_active=True,
            )
        except BankAccount.DoesNotExist:
            transaction_record.status = Transaction.Status.SETTLING
            transaction_record.save(update_fields=['status'])
            logger.warning(
                f"No verified bank account for business {business.id}. "
                f"Transaction {transaction_record.id} set to SETTLING."
            )
            return False

        from apps.payments.services.wallet_service import WalletService
        WalletService.deposit(
            user=owner,
            amount=net_amount,
            description=f'تسویه بیعانه نوبت #{appointment.id} - {appointment.service.name}',
            reference=f'TX-{transaction_record.id}',
        )

        transaction_record.status = Transaction.Status.SETTLED
        transaction_record.settled_at = timezone.now()
        transaction_record.save(update_fields=['status', 'settled_at'])

        logger.info(
            f"Deposit released: appointment={appointment.id}, "
            f"net_amount={net_amount} to owner {owner.phone}"
        )
        return True

    @classmethod
    @transaction.atomic
    def process_refund(cls, transaction_record, refund_amount: int, penalty_amount: int = 0):
        """پردازش استرداد وجه"""
        if transaction_record.status not in [
            Transaction.Status.SUCCESS,
            Transaction.Status.SETTLING,
        ]:
            raise PaymentException(
                message='این تراکنش قابل استرداد نیست',
                code='CANNOT_REFUND',
            )

        if refund_amount > transaction_record.amount:
            raise PaymentException(
                message='مبلغ استرداد نمی‌تواند بیشتر از مبلغ تراکنش باشد',
                code='INVALID_REFUND_AMOUNT',
            )

        user = transaction_record.user

        from apps.payments.services.wallet_service import WalletService
        WalletService.refund_to_wallet(
            user=user,
            amount=refund_amount,
            description=f'استرداد وجه تراکنش #{transaction_record.tracking_code}',
            reference=f'REFUND-{transaction_record.id}',
        )

        if refund_amount >= transaction_record.amount:
            transaction_record.status = Transaction.Status.REFUNDED
            transaction_record.refunded_at = timezone.now()
            transaction_record.save(update_fields=['status', 'refunded_at'])

        logger.info(
            f"Refund processed: tx={transaction_record.id}, "
            f"amount={refund_amount}, penalty={penalty_amount}"
        )

    @classmethod
    def get_business_pending_balance(cls, business) -> dict:
        """
        ✅ بهینه: فقط ۱ کوئری با Conditional Aggregation
        به جای ۷ کوئری جداگانه
        """
        txs = Transaction.objects.filter(
            business=business,
            type__in=[Transaction.Type.DEPOSIT, Transaction.Type.FULL_PAYMENT],
        )

        # ✅ همه محاسبات در یک کوئری
        aggregates = txs.aggregate(
            blocked=Sum(
                Case(
                    When(status=Transaction.Status.SUCCESS, then='net_amount'),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            settling=Sum(
                Case(
                    When(status=Transaction.Status.SETTLING, then='net_amount'),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            settled=Sum(
                Case(
                    When(status=Transaction.Status.SETTLED, then='net_amount'),
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
            pending_commission=Sum(
                Case(
                    When(
                        status__in=[Transaction.Status.SUCCESS, Transaction.Status.SETTLING],
                        then='commission_amount',
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
        )

        return {
            'blocked': aggregates['blocked'] or 0,
            'settling': aggregates['settling'] or 0,
            'settled': aggregates['settled'] or 0,
            'refunded': aggregates['refunded'] or 0,
            'total': aggregates['total'] or 0,
            'pending_commission': aggregates['pending_commission'] or 0,
        }

    @classmethod
    @transaction.atomic
    def request_settlement(cls, business, amount: int = None) -> Settlement:
        """ثبت درخواست تسویه توسط صاحب کسب‌وکار"""
        try:
            bank_account = BankAccount.objects.get(
                business=business,
                status=BankAccount.Status.VERIFIED,
                is_active=True,
            )
        except BankAccount.DoesNotExist:
            raise PaymentException(
                message='حساب بانکی تایید شده‌ای برای تسویه وجود ندارد',
                code='NO_VERIFIED_BANK_ACCOUNT',
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

        pending_settlements = Settlement.objects.filter(
            business=business,
            status__in=[Settlement.Status.PENDING, Settlement.Status.PROCESSING],
        ).exists()

        if pending_settlements:
            raise PaymentException(
                message='شما یک درخواست تسویه در حال پردازش دارید',
                code='PENDING_SETTLEMENT_EXISTS',
            )

        settlement = Settlement.objects.create(
            business=business,
            bank_account=bank_account,
            amount=amount,
            commission_total=balances['pending_commission'],
            status=Settlement.Status.PENDING,
            frequency=Settlement.Frequency.MANUAL,
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
        settlement.processed_at = timezone.now()
        settlement.save(update_fields=['status', 'processed_at'])

        from apps.payments.services.wallet_service import WalletService
        try:
            WalletService.withdraw(
                user=settlement.business.owner,
                amount=settlement.amount,
                description=f'تسویه حساب - #{settlement.id}',
                reference=f'SETTLEMENT-{settlement.id}',
            )
        except Exception as e:
            settlement.status = Settlement.Status.REJECTED
            settlement.rejection_reason = str(e)
            settlement.save(update_fields=['status', 'rejection_reason'])
            logger.error(f"Settlement failed: {e}")
            return False

        settlement.status = Settlement.Status.COMPLETED
        settlement.completed_at = timezone.now()
        settlement.save(update_fields=['status', 'completed_at'])

        # ✅ بهینه: استفاده از bulk update به جای حلقه
        txs = Transaction.objects.filter(
            business=settlement.business,
            status=Transaction.Status.SETTLING,
        ).order_by('created_at')

        remaining = settlement.amount
        tx_ids_to_settle = []

        for tx in txs:
            if remaining <= 0:
                break
            if tx.net_amount <= remaining:
                tx_ids_to_settle.append(tx.id)
                remaining -= tx.net_amount

        if tx_ids_to_settle:
            now = timezone.now()
            Transaction.objects.filter(id__in=tx_ids_to_settle).update(
                status=Transaction.Status.SETTLED,
                settled_at=now,
            )
            settlement.transactions_included.add(*tx_ids_to_settle)

        logger.info(
            f"Settlement completed: id={settlement.id}, amount={settlement.amount}"
        )
        return True

    @classmethod
    def auto_settle_completed_appointments(cls):
        """
        ✅ بهینه: استفاده از Prefetch برای جلوگیری از N+1
        """
        from apps.bookings.models import Appointment

        # ✅ Prefetch کردن transactions مرتبط
        appointments = Appointment.objects.filter(
            status='done',
            deposit_paid=True,
            verified_at__isnull=False,
        ).select_related('business', 'service').prefetch_related(
            Prefetch(
                'transactions',
                queryset=Transaction.objects.filter(
                    type=Transaction.Type.DEPOSIT,
                    status=Transaction.Status.SUCCESS,
                    settled_at__isnull=True,
                ).only('id', 'net_amount', 'status', 'settled_at', 'appointment_id'),
                to_attr='pending_deposits'
            )
        )

        processed = 0
        for appointment in appointments:
            # ✅ استفاده از داده‌های prefetched (بدون کوئری اضافی)
            if hasattr(appointment, 'pending_deposits') and appointment.pending_deposits:
                tx = appointment.pending_deposits[0]
                try:
                    cls.release_deposit(appointment, tx)
                    processed += 1
                except Exception as e:
                    logger.error(
                        f"Auto-settle failed for appointment {appointment.id}: {e}"
                    )

        logger.info(f"Auto-settle completed: {processed} transactions processed")
        return processed