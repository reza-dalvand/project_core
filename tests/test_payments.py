"""
تست‌های سیستم پرداخت و مالی
"""
import pytest
from decimal import Decimal
from django.utils import timezone

from apps.payments.models import (
    Transaction, Wallet, WalletTransaction, BankAccount, Settlement,
)
from apps.payments.services.wallet_service import WalletService
from apps.payments.services.settlement_service import SettlementService
from apps.core.exceptions import InsufficientBalanceException


@pytest.mark.django_db
class TestWalletService:
    """تست‌های سرویس کیف پول"""

    def test_get_or_create_wallet(self, customer_user):
        """ایجاد کیف پول برای کاربر جدید"""
        wallet = WalletService.get_or_create_wallet(customer_user)
        assert wallet is not None
        assert wallet.user == customer_user
        assert wallet.balance == 0

    def test_deposit(self, customer_user):
        """واریز به کیف پول"""
        tx = WalletService.deposit(
            customer_user, 100000, 'شارژ تست', 'REF-001'
        )
        assert tx.amount == 100000
        assert tx.type == WalletTransaction.Type.DEPOSIT

        wallet = Wallet.objects.get(user=customer_user)
        assert wallet.balance == 100000
        assert wallet.total_credit == 100000

    def test_withdraw_success(self, customer_user):
        """برداشت موفق از کیف پول"""
        WalletService.deposit(customer_user, 200000, 'شارژ')

        tx = WalletService.withdraw(customer_user, 50000, 'برداشت تست')
        assert tx.amount == 50000

        wallet = Wallet.objects.get(user=customer_user)
        assert wallet.balance == 150000

    def test_withdraw_insufficient_balance(self, customer_user):
        """برداشت با موجودی ناکافی"""
        WalletService.deposit(customer_user, 10000, 'شارژ')

        with pytest.raises(InsufficientBalanceException):
            WalletService.withdraw(customer_user, 50000)

    def test_wallet_summary(self, customer_user):
        """خلاصه کیف پول"""
        WalletService.deposit(customer_user, 100000, 'شارژ ۱')
        WalletService.deposit(customer_user, 200000, 'شارژ ۲')
        WalletService.withdraw(customer_user, 50000, 'برداشت')

        summary = WalletService.get_wallet_summary(customer_user)
        assert summary['balance'] == 250000
        assert summary['total_credit'] == 300000
        assert summary['total_debit'] == 50000


@pytest.mark.django_db
class TestSettlementService:
    """تست‌های سرویس تسویه"""

    def test_calculate_commission_min(self):
        """محاسبه کارمزد - حداقل"""
        # ۱٪ از ۵۰۰,۰۰۰ = ۵,۰۰۰ → حداقل ۱۰,۰۰۰
        commission = SettlementService.calculate_commission(500000)
        assert commission == 10000  # حداقل

    def test_calculate_commission_percent(self):
        """محاسبه کارمزد - درصدی"""
        # ۱٪ از ۵,۰۰۰,۰۰۰ = ۵۰,۰۰۰
        commission = SettlementService.calculate_commission(5000000)
        assert commission == 50000

    def test_calculate_net_amount(self):
        """محاسبه مبلغ خالص"""
        commission, net = SettlementService.calculate_net_amount(1000000)
        assert commission == 10000  # حداقل
        assert net == 990000

    def test_business_pending_balance(
        self, approved_business_with_service, customer_user
    ):
        """محاسبه مانده‌های کسب‌وکار"""
        data = approved_business_with_service
        business = data['business']

        # ایجاد تراکنش تست
        Transaction.objects.create(
            user=customer_user,
            business=business,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.SUCCESS,
            amount=200000,
            commission_amount=10000,
            net_amount=190000,
        )

        balances = SettlementService.get_business_pending_balance(business)
        assert balances['blocked'] == 190000
        assert balances['total'] == 200000


@pytest.mark.django_db
class TestBankAccount:
    """تست‌های حساب بانکی"""

    def test_create_bank_account(self, business_owner_user):
        """ثبت حساب بانکی"""
        from apps.businesses.models import Business, Province, City, Category

        province = Province.objects.create(name='تهران', slug='tehran')
        city = City.objects.create(name='تهران', slug='tehran-city', province=province)
        category = Category.objects.create(name='سالن', slug='salon')

        business = Business.objects.create(
            owner=business_owner_user,
            name='سالن تست',
            category=category,
            province=province,
            city=city,
            address='آدرس تست',
            status='approved',
        )

        bank = BankAccount.objects.create(
            user=business_owner_user,
            business=business,
            owner_name='کاربر تست',
            national_id='0012345679',
            bank_name='بانک ملی',
            sheba='IR012345678901234567890123',
            card_number='6037991234567890',
            status=BankAccount.Status.PENDING,
        )

        assert bank.status == 'pending'
        assert bank.is_active is True


@pytest.mark.django_db
class TestPaymentAPI:
    """تست‌های API پرداخت"""

    def test_wallet_detail_unauthenticated(self, api_client):
        """دسترسی بدون احراز هویت"""
        url = '/api/v1/payments/wallet/'
        response = api_client.get(url)
        assert response.status_code == 401

    def test_wallet_detail_authenticated(self, authenticated_customer_client):
        """دسترسی با احراز هویت"""
        url = '/api/v1/payments/wallet/'
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_payment_history(self, authenticated_customer_client, customer_user):
        """تاریخچه پرداخت‌ها"""
        # ایجاد تراکنش تست
        Transaction.objects.create(
            user=customer_user,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.SUCCESS,
            amount=200000,
        )

        url = '/api/v1/payments/history/'
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_business_stats_requires_approval(
        self, authenticated_customer_client
    ):
        """آمار مالی نیاز به تایید کسب‌وکار دارد"""
        url = '/api/v1/payments/business/stats/'
        response = authenticated_customer_client.get(url)
        assert response.status_code == 403