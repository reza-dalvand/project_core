"""
Payment Services
"""
from .payment_service import PaymentService


def process_refund(appointment, full_amount=False):
    """
    تابع استرداد برای سازگاری با models

    Args:
        appointment: نوبت مربوطه
        full_amount: اگر True، استرداد کامل (لغو توسط سالن)
                     اگر False، فقط بیعانه
    """
    if full_amount:
        # ✅ بررسی مبلغ واقعاً پرداخت شده
        from apps.payments.models import Transaction
        from django.db.models import Sum

        paid_amount = Transaction.objects.filter(
            appointment=appointment,
            type__in=[
                Transaction.Type.DEPOSIT,
                Transaction.Type.FULL_PAYMENT,
            ],
            status__in=[
                Transaction.Status.BLOCKED,
                Transaction.Status.SETTLING,
                Transaction.Status.SETTLED,
            ],
        ).aggregate(total=Sum('amount'))['total'] or 0

        amount = paid_amount
    else:
        amount = appointment.deposit_amount

    if amount > 0:
        PaymentService.process_refund(
            appointment=appointment,
            refund_amount=amount,
            reason='لغو نوبت',
        )