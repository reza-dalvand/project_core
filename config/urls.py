from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # 1️⃣ Django Admin + Jazzmin (برای مدیران ارشد و پشتیبانی سایت معرفی)
    path('admin/', admin.site.urls),

    # 2️⃣ سایت معرفی (Landing)
    path('', include('apps.landing.urls')),

    # 3️⃣ پنل ادمین اپ (Dashboard - برای ادمین‌های اپلیکیشن)
    path('dashboard/', include('apps.dashboard.urls')),

    # 4️⃣ REST API برای اپ موبایل
    path('api/v1/', include('apps.api.urls')),
]
