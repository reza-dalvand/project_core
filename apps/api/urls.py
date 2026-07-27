"""
URL configuration for API app
"""
from django.urls import path, include

app_name = 'api'

urlpatterns = [
    # Accounts & Auth
    path('accounts/', include('apps.accounts.urls')),

    # Businesses
    path('businesses/', include('apps.businesses.urls')),

    # Bookings (بعداً)
    # path('bookings/', include('apps.bookings.urls')),

    # Payments (بعداً)
    # path('payments/', include('apps.payments.urls')),

    # Reviews (بعداً)
    # path('reviews/', include('apps.reviews.urls')),
]