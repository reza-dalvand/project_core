from django.urls import path
from .views import ProvinceListView, CityListView

app_name = 'locations'

urlpatterns = [
    path('provinces/', ProvinceListView.as_view(), name='province-list'),
    path('provinces/<int:province_id>/cities/', CityListView.as_view(), name='city-list'),
]