from django.urls import path
from .views.business import (
    BusinessCreateView,
    BusinessListView,
    BusinessStatusView,
    BusinessDetailView,
    BusinessBankInfoView,
    BusinessDeleteView,
    PublicBusinessDetailView,
    BusinessGalleryListView,
    BusinessGalleryUploadView,
    BusinessGalleryDeleteView,
    BusinessGalleryReorderView,
)

app_name = 'businesses'

urlpatterns = [
    # ═══════════ Business Registration ═══════════
    path('create/', BusinessCreateView.as_view(), name='business-create'),
    path('list/', BusinessListView.as_view(), name='business-list'),
    path('status/', BusinessStatusView.as_view(), name='business-status'),
    
    # ═══════════ Business Management ═══════════
    path('detail/', BusinessDetailView.as_view(), name='business-detail'),
    path('bank-info/', BusinessBankInfoView.as_view(), name='bank-info'),
    path('delete/', BusinessDeleteView.as_view(), name='business-delete'),
    
    # ═══════════ Gallery Management ═══════════
    path('gallery/', BusinessGalleryListView.as_view(), name='gallery-list'),
    path('gallery/upload/', BusinessGalleryUploadView.as_view(), name='gallery-upload'),
    path('gallery/<int:pk>/delete/', BusinessGalleryDeleteView.as_view(), name='gallery-delete'),
    path('gallery/reorder/', BusinessGalleryReorderView.as_view(), name='gallery-reorder'),
    
    # ═══════════ Public ═══════════
    path('public/<slug:booking_slug>/', PublicBusinessDetailView.as_view(), name='public-business-detail'),
]