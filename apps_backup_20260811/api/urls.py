"""
URL configuration for API app - نسخه نهایی
"""
from django.urls import path, include

app_name = 'api'

urlpatterns = [
    path('accounts/', include('apps.accounts.urls')),
    path('businesses/', include('apps.businesses.urls')),
    path('bookings/', include('apps.bookings.urls')),
    path('payments/', include('apps.payments.urls')),
    path('reviews/', include('apps.reviews.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('', include('apps.advanced.urls')),  # ✅ ویژگی‌های پیشرفته
]