# در apps/payments/services/transaction_service.py
from apps.payments.models import Transaction


class TransactionService:
    @classmethod
    def calculate_commission(cls, transaction):
        if transaction.amount > 0 and transaction.commission_amount == 0:
            if transaction.type in [Transaction.Type.DEPOSIT, Transaction.Type.FULL_PAYMENT]:
                transaction.commission_amount = int(transaction.amount * 0.05)
                transaction.net_amount = transaction.amount - transaction.commission_amount