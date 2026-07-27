"""
سرویس کیف پول
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.payments.models import Wallet, WalletTransaction
from apps.core.exceptions import (
    InsufficientBalanceException,
    PaymentException,
)

logger = logging.getLogger(__name__)


class WalletService:
    """سرویس مدیریت کیف پول"""

    @classmethod
    def get_or_create_wallet(cls, user) -> Wallet:
        """دریافت یا ایجاد کیف پول برای کاربر"""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={'balance': 0}
        )
        if created:
            logger.info(f"Wallet created for user {user.phone}")
        return wallet

    @classmethod
    @transaction.atomic
    def deposit(cls, user, amount: int, description: str = '', reference: str = '') -> WalletTransaction:
        """
        واریز به کیف پول

        Args:
            user: کاربر
            amount: مبلغ به تومان
            description: توضیحات
            reference: ارجاع (مثلاً شناسه تراکنش)

        Returns:
            WalletTransaction: تراکنش ایجاد شده
        """
        if amount <= 0:
            raise PaymentException(
                message='مبلغ واریزی باید بیشتر از صفر باشد',
                code='INVALID_AMOUNT',
            )

        wallet = cls.get_or_create_wallet(user)

        if wallet.is_frozen:
            raise PaymentException(
                message='کیف پول شما مسدود است. لطفاً با پشتیبانی تماس بگیرید',
                code='WALLET_FROZEN',
            )

        # بروزرسانی موجودی
        wallet.balance += amount
        wallet.total_credit += amount
        wallet.save(update_fields=['balance', 'total_credit', 'updated_at'])

        # ایجاد تراکنش
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            type=WalletTransaction.Type.DEPOSIT,
            description=description or 'شارژ کیف پول',
            balance_after=wallet.balance,
            reference=reference,
        )

        logger.info(
            f"Wallet deposit: user={user.phone}, amount={amount}, "
            f"balance={wallet.balance}"
        )

        return tx

    @classmethod
    @transaction.atomic
    def withdraw(cls, user, amount: int, description: str = '', reference: str = '') -> WalletTransaction:
        """
        برداشت از کیف پول

        Args:
            user: کاربر
            amount: مبلغ به تومان
            description: توضیحات
            reference: ارجاع

        Returns:
            WalletTransaction: تراکنش ایجاد شده
        """
        if amount <= 0:
            raise PaymentException(
                message='مبلغ برداشتی باید بیشتر از صفر باشد',
                code='INVALID_AMOUNT',
            )

        wallet = cls.get_or_create_wallet(user)

        if wallet.is_frozen:
            raise PaymentException(
                message='کیف پول شما مسدود است',
                code='WALLET_FROZEN',
            )

        if wallet.balance < amount:
            raise InsufficientBalanceException(
                message=f'موجودی کیف پول کافی نیست. موجودی فعلی: {wallet.balance:,} تومان',
                details={
                    'balance': wallet.balance,
                    'requested': amount,
                    'shortage': amount - wallet.balance,
                },
            )

        # بروزرسانی موجودی
        wallet.balance -= amount
        wallet.total_debit += amount
        wallet.save(update_fields=['balance', 'total_debit', 'updated_at'])

        # ایجاد تراکنش
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            type=WalletTransaction.Type.WITHDRAWAL,
            description=description or 'برداشت از کیف پول',
            balance_after=wallet.balance,
            reference=reference,
        )

        logger.info(
            f"Wallet withdraw: user={user.phone}, amount={amount}, "
            f"balance={wallet.balance}"
        )

        return tx

    @classmethod
    @transaction.atomic
    def pay_from_wallet(cls, user, amount: int, description: str = '', reference: str = '') -> WalletTransaction:
        """
        پرداخت از کیف پول (مثل خرید خدمت یا بیعانه)
        """
        tx = cls.withdraw(user, amount, description or 'پرداخت از کیف پول', reference)
        return tx

    @classmethod
    @transaction.atomic
    def refund_to_wallet(cls, user, amount: int, description: str = '', reference: str = '') -> WalletTransaction:
        """
        استرداد وجه به کیف پول
        """
        tx = cls.deposit(user, amount, description or 'استرداد وجه به کیف پول', reference)

        # بروزرسانی نوع تراکنش به refund
        tx.type = WalletTransaction.Type.REFUND
        tx.save(update_fields=['type'])

        return tx

    @classmethod
    def get_balance(cls, user) -> int:
        """دریافت موجودی کیف پول"""
        wallet = cls.get_or_create_wallet(user)
        return wallet.balance

    @classmethod
    def get_wallet_summary(cls, user) -> dict:
        """خلاصه وضعیت کیف پول"""
        wallet = cls.get_or_create_wallet(user)

        # آمار ۳۰ روز اخیر
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent_txs = WalletTransaction.objects.filter(
            wallet=wallet,
            created_at__gte=thirty_days_ago,
        )

        total_deposits = sum(
            tx.amount for tx in recent_txs
            if tx.type in [WalletTransaction.Type.DEPOSIT, WalletTransaction.Type.REFUND]
        )
        total_withdrawals = sum(
            tx.amount for tx in recent_txs
            if tx.type == WalletTransaction.Type.WITHDRAWAL
        )

        return {
            'balance': wallet.balance,
            'total_credit': wallet.total_credit,
            'total_debit': wallet.total_debit,
            'is_frozen': wallet.is_frozen,
            'recent_deposits': total_deposits,
            'recent_withdrawals': total_withdrawals,
            'recent_transactions_count': recent_txs.count(),
        }