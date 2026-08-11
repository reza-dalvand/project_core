"""
URL configuration for businesses app
"""
from django.urls import path
from .views.business import (
    ProvinceListView,
    CityListView,
    CategoryListView,
    NationalIdVerificationView,
    BusinessCreateView,
    BusinessStatusView,
    BusinessDetailView,
    ImageUploadView,
    BusinessDeleteView,
)
from .views.service import (
    ServiceListView,
    ServiceDetailView,
    ServiceToggleActiveView,
)
from .views.employee import (
    EmployeeListView,
    EmployeeDetailView,
    EmployeeToggleActiveView,
    EmployeeAssignServicesView,
)
from .views.schedule import (
    ScheduleListView,
    ScheduleDetailView,
    WeeklyScheduleView,
)
from .views.portfolio import (
    PortfolioListView,
    PortfolioDetailView,
    PortfolioToggleActiveView,
    PortfolioReorderView,
)

app_name = 'businesses'

urlpatterns = [
    # ═══════════ Lookup Endpoints ═══════════
    path('provinces/', ProvinceListView.as_view(), name='province-list'),
    path('provinces/<int:province_id>/cities/', CityListView.as_view(), name='city-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),

    # ═══════════ National ID Verification ═══════════
    path('verify-national-id/', NationalIdVerificationView.as_view(), name='verify-national-id'),

    # ═══════════ Business Registration ═══════════
    path('create/', BusinessCreateView.as_view(), name='business-create'),
    path('status/', BusinessStatusView.as_view(), name='business-status'),

    # ═══════════ Business Management ═══════════
    path('detail/', BusinessDetailView.as_view(), name='business-detail'),
    path('upload-image/', ImageUploadView.as_view(), name='upload-image'),
    path('delete/', BusinessDeleteView.as_view(), name='business-delete'),

    # ═══════════ Services Management ═══════════
    path('services/', ServiceListView.as_view(), name='service-list'),
    path('services/<int:pk>/', ServiceDetailView.as_view(), name='service-detail'),
    path('services/<int:pk>/toggle-active/', ServiceToggleActiveView.as_view(), name='service-toggle-active'),

    # ═══════════ Employees Management ═══════════
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/<int:pk>/toggle-active/', EmployeeToggleActiveView.as_view(), name='employee-toggle-active'),
    path('employees/<int:pk>/assign-services/', EmployeeAssignServicesView.as_view(), name='employee-assign-services'),

    # ═══════════ Schedule Management ═══════════
    path('schedules/', ScheduleListView.as_view(), name='schedule-list'),
    path('schedules/<int:pk>/', ScheduleDetailView.as_view(), name='schedule-detail'),
    path('schedules/weekly/', WeeklyScheduleView.as_view(), name='weekly-schedule'),

    # ═══════════ Portfolio Management ═══════════
    path('portfolios/', PortfolioListView.as_view(), name='portfolio-list'),
    path('portfolios/<int:pk>/', PortfolioDetailView.as_view(), name='portfolio-detail'),
    path('portfolios/<int:pk>/toggle-active/', PortfolioToggleActiveView.as_view(), name='portfolio-toggle-active'),
    path('portfolios/reorder/', PortfolioReorderView.as_view(), name='portfolio-reorder'),
]