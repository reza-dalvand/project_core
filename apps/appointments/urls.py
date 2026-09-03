from django.urls import path
from .views import (
    CreateAppointmentView,
    CustomerAppointmentsView,
    BusinessAppointmentsView,
    AppointmentDetailView,
    CancelAppointmentView,
    CancelByBusinessView,
    VerifyServiceCodeView,
    RegenerateCodeView,
    AppointmentStatsView,
    BusinessTodayAppointmentsView,
    
)

app_name = 'appointments'

urlpatterns = [
    # ═══════════ Booking ═══════════
    path('create/', CreateAppointmentView.as_view(), name='create-appointment'),
    path('my-appointments/', CustomerAppointmentsView.as_view(), name='my-appointments'),
    path('business-appointments/', BusinessAppointmentsView.as_view(), name='business-appointments'),
    path('business-today/', BusinessTodayAppointmentsView.as_view(), name='business-today-appointments'),  # ← جدید
    path('business-stats/', AppointmentStatsView.as_view(), name='business-stats'),
    path('<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),

    # ═══════════ Customer Actions ═══════════
    path('<int:pk>/cancel/', CancelAppointmentView.as_view(), name='cancel-appointment'),
    path('<int:pk>/regenerate-code/', RegenerateCodeView.as_view(), name='regenerate-code'),

    # ═══════════ Business Actions ═══════════
    path('<int:pk>/cancel-by-business/', CancelByBusinessView.as_view(), name='cancel-by-business'),
    path('<int:pk>/verify-code/', VerifyServiceCodeView.as_view(), name='verify-code'),
]