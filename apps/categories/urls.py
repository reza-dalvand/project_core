from django.urls import path
from .views import ServiceCategoryListView, BusinessCategoryListView

app_name = 'categories'

urlpatterns = [
    path('service-categories/', ServiceCategoryListView.as_view(), name='service-category-list'),
    path('business-categories/', BusinessCategoryListView.as_view(), name='business-category-list'),
]