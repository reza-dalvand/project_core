"""
URL configuration for payments app
"""
from django.urls import path
from .views.gateway import InitiatePaymentView, PaymentCallbackView
from .views.wallet import (
    WalletDetailView,
    WalletSummaryView,
    WalletTransactionListView,
    WalletChargeView,
    WalletChargeCallbackView,
)
from .views.bank import BankAccountView
from .views.settlement import (
    BusinessFinancialStatsView,
    SettlementRequestView,
    SettlementListView,
    AdminSettlementListView,
    AdminSettlementProcessView,
)
from .views.history import (
    CustomerPaymentHistoryView,
    CustomerTransactionDetailView,
    BusinessTransactionListView,
)

app_name = 'payments'

urlpatterns = [
    # ═══════════ Gateway ═══════════
    path('initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('callback/', PaymentCallbackView.as_view(), name='payment-callback'),

    # ═══════════ Wallet ═══════════
    path('wallet/', WalletDetailView.as_view(), name='wallet-detail'),
    path('wallet/summary/', WalletSummaryView.as_view(), name='wallet-summary'),
    path('wallet/transactions/', WalletTransactionListView.as_view(), name='wallet-transactions'),
    path('wallet/charge/', WalletChargeView.as_view(), name='wallet-charge'),
    path('wallet/callback/', WalletChargeCallbackView.as_view(), name='wallet-callback'),

    # ═══════════ Customer History ═══════════
    path('history/', CustomerPaymentHistoryView.as_view(), name='payment-history'),
    path('history/<int:pk>/', CustomerTransactionDetailView.as_view(), name='transaction-detail'),

    # ═══════════ Business Financial ═══════════
    path('business/stats/', BusinessFinancialStatsView.as_view(), name='business-stats'),
    path('business/transactions/', BusinessTransactionListView.as_view(), name='business-transactions'),
    path('business/bank-account/', BankAccountView.as_view(), name='bank-account'),
    path('business/settlement/request/', SettlementRequestView.as_view(), name='settlement-request'),
    path('business/settlements/', SettlementListView.as_view(), name='settlement-list'),

    # ═══════════ Admin ═══════════
    path('admin/settlements/pending/', AdminSettlementListView.as_view(), name='admin-settlements-pending'),
    path('admin/settlements/<int:pk>/process/', AdminSettlementProcessView.as_view(), name='admin-settlement-process'),
]