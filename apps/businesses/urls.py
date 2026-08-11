from django.urls import path
from .views.business import (
    BusinessCreateView,
    BusinessStatusView,
    BusinessDetailView,
    BusinessBankInfoView,
    BusinessDeleteView,
    PublicBusinessDetailView,
)

app_name = 'businesses'

urlpatterns = [
    # ═══════════ Business Registration ═══════════
    path('create/', BusinessCreateView.as_view(), name='business-create'),
    path('status/', BusinessStatusView.as_view(), name='business-status'),

    # ═══════════ Business Management ═══════════
    path('detail/', BusinessDetailView.as_view(), name='business-detail'),
    path('bank-info/', BusinessBankInfoView.as_view(), name='bank-info'),
    path('delete/', BusinessDeleteView.as_view(), name='business-delete'),

    # ═══════════ Public ═══════════
    path('public/<slug:booking_slug>/', PublicBusinessDetailView.as_view(), name='public-business-detail'),
]