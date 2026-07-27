"""
URL configuration for advanced features
"""
from django.urls import path
from .views.search_views import (
    SearchView,
    SearchSuggestionsView,
    SearchHistoryView,
    SearchHistoryDeleteView,
)
from .views.favorite_views import (
    FavoriteToggleView,
    FavoriteListView,
    FavoriteCheckView,
    FavoriteCountView,
)
from .views.referral_views import (
    ReferralCodeView,
    ReferralApplyView,
    ReferralStatsView,
    ReferralListView,
)
from .views.geolocation_views import NearbyBusinessesView
from .views.report_views import (
    ReportCreateView,
    ReportListView,
    ReportDeleteView,
)

app_name = 'advanced'

urlpatterns = [
    # ═══════════ Search ═══════════
    path('search/', SearchView.as_view(), name='search'),
    path('search/suggestions/', SearchSuggestionsView.as_view(), name='search-suggestions'),
    path('search/history/', SearchHistoryView.as_view(), name='search-history'),
    path('search/history/<int:pk>/', SearchHistoryDeleteView.as_view(), name='search-history-delete'),

    # ═══════════ Favorites ═══════════
    path('favorites/', FavoriteListView.as_view(), name='favorite-list'),
    path('favorites/toggle/', FavoriteToggleView.as_view(), name='favorite-toggle'),
    path('favorites/check/', FavoriteCheckView.as_view(), name='favorite-check'),
    path('favorites/count/', FavoriteCountView.as_view(), name='favorite-count'),

    # ═══════════ Referral ═══════════
    path('referral/code/', ReferralCodeView.as_view(), name='referral-code'),
    path('referral/apply/', ReferralApplyView.as_view(), name='referral-apply'),
    path('referral/stats/', ReferralStatsView.as_view(), name='referral-stats'),
    path('referral/list/', ReferralListView.as_view(), name='referral-list'),

    # ═══════════ Geolocation ═══════════
    path('nearby/', NearbyBusinessesView.as_view(), name='nearby-businesses'),

    # ═══════════ Reports ═══════════
    path('reports/', ReportListView.as_view(), name='report-list'),
    path('reports/create/', ReportCreateView.as_view(), name='report-create'),
    path('reports/<int:pk>/', ReportDeleteView.as_view(), name='report-delete'),
]