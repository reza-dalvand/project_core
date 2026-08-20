"""
تست‌های سیستم پرداخت — ساده‌سازی شده
"""
import pytest
from django.urls import reverse

from apps.payments.models import Transaction, Settlement


@pytest.mark.django_db
class TestPaymentService:
    def test_calculate_app_fee(self):
        from apps.payments.services.payment_service import PaymentService
        fee = PaymentService.calculate_app_fee(500000)
        assert fee >= 10000

    def test_calculate_app_fee_small(self):
        from apps.payments.services.payment_service import PaymentService
        fee = PaymentService.calculate_app_fee(50000)
        assert fee == 7000  # حداقل

    def test_business_pending_balance(self, approved_business, customer_user):
        from apps.payments.services.payment_service import PaymentService
        Transaction.objects.create(
            business=approved_business,
            customer=customer_user,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.BLOCKED,
            amount=200000,
            app_fee=10000,
        )
        balances = PaymentService.get_business_pending_balance(approved_business)
        assert balances['blocked'] == 200000
        assert balances['total'] == 200000


@pytest.mark.django_db
class TestTransactionModel:
    def test_create_transaction(self, customer_user, approved_business):
        tx = Transaction.objects.create(
            business=approved_business,
            customer=customer_user,
            type='deposit',
            amount=100000,
            app_fee=10000,
        )
        assert tx.tracking_code.startswith('TRK-')
        assert tx.ref_number.startswith('REF-')
        assert tx.status == 'blocked'

    def test_no_wallet(self):
        """Wallet دیگر وجود ندارد"""
        from apps.payments.models import Transaction
        types = [c[0] for c in Transaction.Type.choices]
        assert 'wallet_topup' not in types


@pytest.mark.django_db
class TestSettlementModel:
    def test_create_settlement(self, approved_business):
        settlement = Settlement.objects.create(
            business=approved_business,
            amount=500000,
            bank_sheba='IR123456789012345678901234',
            bank_name='بانک ملی',
        )
        assert settlement.status == 'pending'


@pytest.mark.django_db
class TestPaymentAPI:
    def test_payment_history(self, authenticated_customer_client, customer_user, approved_business):
        Transaction.objects.create(
            business=approved_business,
            customer=customer_user,
            type='deposit',
            amount=200000,
        )
        url = reverse('payments:payment-history')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200

    def test_business_stats(self, authenticated_business_client, approved_business):
        url = reverse('payments:business-stats')
        response = authenticated_business_client.get(url)
        assert response.status_code == 200