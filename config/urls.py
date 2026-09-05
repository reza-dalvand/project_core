"""
URL Configuration - بیو کلاب — نسخه نهایی کامل
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.core.admin_site import OTPAdminSite
from apps.dashboard.views.errors import error_403, error_404, error_500


urlpatterns = [
    # ═══════ Landing Page ═══════
    path('', include('apps.landing.urls')),
    # ═══════ Dashboard ═══════
    path('dashboard/', include('apps.dashboard.urls')),
    # ═══════ REST API ═══════
    path('api/v1/', include([
        path('accounts/', include('apps.accounts.urls')),
        path('categories/', include('apps.categories.urls')),
        path('locations/', include('apps.locations.urls')),
        path('businesses/', include('apps.businesses.urls')),
        path('services/', include('apps.services.urls')),
        path('schedules/', include('apps.schedules.urls')),
        path('appointments/', include('apps.appointments.urls')),
        path('payments/', include('apps.payments.urls')),
        path('reviews/', include('apps.reviews.urls')),
        path('favorites/', include('apps.favorites.urls')),
        path('notifications/', include('apps.notifications.urls')),
        path('search/', include('apps.search.urls')),
        path('portfolios/', include('apps.portfolios.urls')),
        path('ads/', include('apps.ads.urls')),
        path('reminders/', include('apps.reminders.urls')),
        path('support/', include('apps.support.urls')),

        # ✅ فاز ۱: اندپوینت‌های کانفیگ
        path('config/', include('apps.core.urls')),
    ])),
]

# ═══════ Media & Static در توسعه ═══════
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ═══════ DRF Spectacular ═══════
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

handler403 = error_403
handler404 = error_404
handler500 = error_500