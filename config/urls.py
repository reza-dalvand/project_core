"""
URL Configuration - Single Admin Site with Jazzmin
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ═══════ سفارشی‌سازی Admin Site اصلی ═══════
admin.site.site_header = "پنل مدیریت زیبانو"
admin.site.site_title = "زیبانو | مدیریت"
admin.site.index_title = "داشبورد مدیریت"

urlpatterns = [
    # ═══════ Admin Site واحد با Jazzmin ═══════
    path(
        settings.LANDING_ADMIN_URL,  # از env می‌خواند (مثلاً admin/)
        admin.site.urls,
        name='admin',
    ),

    # ═══════ Landing Page (سایت معرفی) ═══════
    path('', include('apps.landing.urls')),

    # ═══════ REST API ═══════
    path('api/v1/', include('apps.api.urls')),
]

# ═══════ Media & Static در توسعه ═══════
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # DRF Spectacular (Swagger)
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