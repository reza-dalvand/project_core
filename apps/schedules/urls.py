from django.urls import path
from .views import (
    ScheduleListView,
    ScheduleDetailView,
    ScheduleByDateView,
)

app_name = 'schedules'

urlpatterns = [
    path('', ScheduleListView.as_view(), name='schedule-list'),
    path('<int:pk>/', ScheduleDetailView.as_view(), name='schedule-detail'),
    path('by-date/', ScheduleByDateView.as_view(), name='schedule-by-date'),
]