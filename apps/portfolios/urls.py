from django.urls import path
from .views import (
    PortfolioListView,
    PortfolioDetailView,
    BusinessPortfolioCreateView,
    BusinessPortfolioListView,
    BusinessPortfolioUpdateView,
    BusinessPortfolioDeleteView,
)

app_name = 'portfolios'

urlpatterns = [
    # Public
    path('', PortfolioListView.as_view(), name='portfolio-list'),
    path('<int:pk>/', PortfolioDetailView.as_view(), name='portfolio-detail'),
    
    # Business
    path('my-portfolios/', BusinessPortfolioListView.as_view(), name='my-portfolio-list'),
    path('my-portfolios/create/', BusinessPortfolioCreateView.as_view(), name='portfolio-create'),
    path('my-portfolios/<int:pk>/update/', BusinessPortfolioUpdateView.as_view(), name='portfolio-update'),
    path('my-portfolios/<int:pk>/delete/', BusinessPortfolioDeleteView.as_view(), name='portfolio-delete'),
]