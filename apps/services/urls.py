from django.urls import path
from .views import (
    ServiceListView,
    ServiceDetailView,
    ServiceToggleActiveView,
)

app_name = 'services'

urlpatterns = [
    path('', ServiceListView.as_view(), name='service-list'),
    path('<int:pk>/', ServiceDetailView.as_view(), name='service-detail'),
    path('<int:pk>/toggle-active/', ServiceToggleActiveView.as_view(), name='service-toggle-active'),
]