from django.urls import path
from .views import (
    InitiatePaymentView,
    PaymentCallbackView,
    CustomerPaymentHistoryView,
    CustomerTransactionDetailView,
    BusinessTransactionListView,
    BusinessFinancialStatsView,
    SettlementRequestView,
    SettlementListView,
)

app_name = 'payments'

urlpatterns = [
    # ═══════════ Gateway ═══════════
    path('initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('callback/', PaymentCallbackView.as_view(), name='payment-callback'), 

    # ═══════════ Customer History ═══════════
    path('history/', CustomerPaymentHistoryView.as_view(), name='payment-history'),
    path('history/<int:pk>/', CustomerTransactionDetailView.as_view(), name='transaction-detail'),

    # ═══════════ Business Financial ═══════════
    path('business/stats/', BusinessFinancialStatsView.as_view(), name='business-stats'),
    path('business/transactions/', BusinessTransactionListView.as_view(), name='business-transactions'),
    path('business/settlement/request/', SettlementRequestView.as_view(), name='settlement-request'),
    path('business/settlements/', SettlementListView.as_view(), name='settlement-list'),
]