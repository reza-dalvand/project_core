"""
URL configuration for project_core.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1️⃣ پنل ادمین سایت معرفی (فعلاً از admin پیش‌فرض استفاده می‌کنیم، بعداً Jazzmin اختصاصی جایگزین می‌شود)
    path(settings.LANDING_ADMIN_URL, admin.site.urls),

    # 2️⃣ سایت معرفی (Landing Page)
    path('', include('apps.landing.urls')),

    # 3️⃣ پنل ادمین اپلیکیشن (Dashboard) - بعداً فعال می‌شود
    # path(settings.DASHBOARD_ADMIN_URL, include('apps.dashboard.urls')),

    # 4️⃣ REST API برای اپلیکیشن موبایل
    path('api/v1/', include('apps.api.urls')),
]

# ─── Serve Media & Static Files in Development ───
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)