from django.urls import path
from .views import AdBannerListView

app_name = 'ads_management'

urlpatterns = [
    path('banners/', AdBannerListView.as_view(), name='banner-list'),
]