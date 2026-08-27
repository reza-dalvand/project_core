from django.urls import path

from .views.config_views import AppVersionView, MaintenanceStatusView

app_name = 'core'

urlpatterns = [
    path('app-version/', AppVersionView.as_view(), name='app-version'),
    path('maintenance-status/', MaintenanceStatusView.as_view(), name='maintenance-status'),
]