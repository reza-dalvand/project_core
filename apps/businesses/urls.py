"""
URL configuration for businesses app
"""
from django.urls import path
from .views.business import (
    ProvinceListView,
    CityListView,
    CategoryListView,
    NationalIdVerificationView,
    BusinessCreateView,
    BusinessStatusView,
    BusinessDetailView,
    ImageUploadView,
    BusinessDeleteView,
)

app_name = 'businesses'

urlpatterns = [
    # ═══════════ Lookup Endpoints ═══════════
    path('provinces/', ProvinceListView.as_view(), name='province-list'),
    path('provinces/<int:province_id>/cities/', CityListView.as_view(), name='city-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),

    # ═══════════ National ID Verification ═══════════
    path('verify-national-id/', NationalIdVerificationView.as_view(), name='verify-national-id'),

    # ═══════════ Business Registration ═══════════
    path('create/', BusinessCreateView.as_view(), name='business-create'),
    path('status/', BusinessStatusView.as_view(), name='business-status'),

    # ═══════════ Business Management ═══════════
    path('detail/', BusinessDetailView.as_view(), name='business-detail'),
    path('upload-image/', ImageUploadView.as_view(), name='upload-image'),
    path('delete/', BusinessDeleteView.as_view(), name='business-delete'),
]