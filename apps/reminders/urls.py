from django.urls import path
from .views import RenewalReminderListView, CustomerRenewalReminderListView

app_name = 'reminders'

urlpatterns = [
    path('', RenewalReminderListView.as_view(), name='business-reminder-list'),
    path('my-reminders/', CustomerRenewalReminderListView.as_view(), name='customer-reminder-list'),
]