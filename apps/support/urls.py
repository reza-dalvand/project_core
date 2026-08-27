from django.urls import path
from .views import (
    FAQListView,
    SupportTicketCreateView,
    SupportTicketListView,
    SupportTicketDetailView,
)

app_name = 'support'

urlpatterns = [
    path('faq/', FAQListView.as_view(), name='faq-list'),
    path('tickets/', SupportTicketListView.as_view(), name='ticket-list'),
    path('tickets/create/', SupportTicketCreateView.as_view(), name='ticket-create'),
    path('tickets/<int:pk>/', SupportTicketDetailView.as_view(), name='ticket-detail'),
]