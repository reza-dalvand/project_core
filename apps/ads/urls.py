from django.urls import path
from .views import (
    ModelRequestListView,
    ModelRequestDetailView,
    BusinessModelRequestCreateView,
    BusinessModelRequestListView,
    BusinessModelRequestUpdateView,
    BusinessModelRequestDeleteView,
    LineRentalListView,
    LineRentalDetailView,
    BusinessLineRentalCreateView,
    BusinessLineRentalListView,
    BusinessLineRentalUpdateView,
    BusinessLineRentalDeleteView,
)

app_name = 'ads'

urlpatterns = [
    # ═══ Model Requests - Public ═══
    path('model-requests/', ModelRequestListView.as_view(), name='model-request-list'),
    path('model-requests/<int:pk>/', ModelRequestDetailView.as_view(), name='model-request-detail'),
    
    # ═══ Model Requests - Business ═══
    path('my-model-requests/', BusinessModelRequestListView.as_view(), name='my-model-request-list'),
    path('my-model-requests/create/', BusinessModelRequestCreateView.as_view(), name='model-request-create'),
    path('my-model-requests/<int:pk>/update/', BusinessModelRequestUpdateView.as_view(), name='model-request-update'),
    path('my-model-requests/<int:pk>/delete/', BusinessModelRequestDeleteView.as_view(), name='model-request-delete'),
    
    # ═══ Line Rentals - Public ═══
    path('line-rentals/', LineRentalListView.as_view(), name='line-rental-list'),
    path('line-rentals/<int:pk>/', LineRentalDetailView.as_view(), name='line-rental-detail'),
    
    # ═══ Line Rentals - Business ═══
    path('my-line-rentals/', BusinessLineRentalListView.as_view(), name='my-line-rental-list'),
    path('my-line-rentals/create/', BusinessLineRentalCreateView.as_view(), name='line-rental-create'),
    path('my-line-rentals/<int:pk>/update/', BusinessLineRentalUpdateView.as_view(), name='line-rental-update'),
    path('my-line-rentals/<int:pk>/delete/', BusinessLineRentalDeleteView.as_view(), name='line-rental-delete'),
]