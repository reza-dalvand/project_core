from django.urls import path
from .views import ServiceCategoryListView, ServiceCategoryListView

app_name = 'categories'

urlpatterns = [
    path('service-categories/', ServiceCategoryListView.as_view(), name='service-category-list'),
    path('business-categories/', ServiceCategoryListView.as_view(), name='business-category-list'),
]