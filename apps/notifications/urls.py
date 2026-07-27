"""
URL configuration for notifications app
"""
from django.urls import path
from .views import (
    NotificationListView,
    NotificationCountView,
    MarkAsReadView,
    DeleteNotificationView,
    DeleteAllNotificationsView,
)

app_name = 'notifications'

urlpatterns = [
    # لیست اعلان‌ها
    path('', NotificationListView.as_view(), name='notification-list'),

    # تعداد اعلان‌ها
    path('count/', NotificationCountView.as_view(), name='notification-count'),

    # خوانده شده
    path('mark-read/', MarkAsReadView.as_view(), name='mark-read'),

    # حذف همه
    path('delete-all/', DeleteAllNotificationsView.as_view(), name='delete-all'),

    # حذف تکی
    path('<int:pk>/', DeleteNotificationView.as_view(), name='delete-notification'),
]