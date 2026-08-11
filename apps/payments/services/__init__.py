"""
Payment Services
"""
from .payment_service import PaymentService

def process_refund(appointment, full_amount=False):
    """تابع استرداد برای سازگاری با models"""
    amount = appointment.deposit_amount
    if full_amount:
        amount = appointment.total_price
    if amount > 0:
        PaymentService.process_refund(
            appointment=appointment,
            refund_amount=amount,
            reason='لغو نوبت',
        )