"""
URL configuration for bookings app
"""
from django.urls import path
from .views.slot import AvailableDatesView, AvailableSlotsView
from .views.booking import (
    CreateBookingView,
    CustomerAppointmentsView,
    BusinessAppointmentsView,
    AppointmentDetailView,
    CancelBookingView,
    CancelByBusinessView,
    VerifyServiceCodeView,
    RegenerateCodeView,
    AppointmentStatsView,
)

app_name = 'bookings'

urlpatterns = [
    # ═══════════ Slots ═══════════
    path('available-dates/', AvailableDatesView.as_view(), name='available-dates'),
    path('available-slots/', AvailableSlotsView.as_view(), name='available-slots'),

    # ═══════════ Booking ═══════════
    path('create/', CreateBookingView.as_view(), name='create-booking'),
    path('my-appointments/', CustomerAppointmentsView.as_view(), name='my-appointments'),
    path('business-appointments/', BusinessAppointmentsView.as_view(), name='business-appointments'),
    path('business-stats/', AppointmentStatsView.as_view(), name='business-stats'),
    path('<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),

    # ═══════════ Customer Actions ═══════════
    path('<int:pk>/cancel/', CancelBookingView.as_view(), name='cancel-booking'),
    path('<int:pk>/regenerate-code/', RegenerateCodeView.as_view(), name='regenerate-code'),

    # ═══════════ Business Actions ═══════════
    path('<int:pk>/cancel-by-business/', CancelByBusinessView.as_view(), name='cancel-by-business'),
    path('<int:pk>/verify-code/', VerifyServiceCodeView.as_view(), name='verify-code'),
]