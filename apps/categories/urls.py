from django.urls import path
from .views import (
    ServiceCategoryListView,
    SubServiceListView,
    BusinessCategoryListView,
)

app_name = 'categories'

urlpatterns = [
    # دسته‌بندی‌های خدمات (همراه زیرخدمات تودرتو)
    path('service-categories/', ServiceCategoryListView.as_view(), name='service-category-list'),

    # 🆕 زیرخدمات — هر دو سبک مسیر تا فرانت هر کدام را صدا زد جواب بگیرد
    path('sub-services/', SubServiceListView.as_view(), name='sub-service-list'),
    path('service-categories/<int:category_id>/sub-services/',
         SubServiceListView.as_view(), name='sub-service-by-category'),

    # 🆕 انواع کسب‌وکار (قبلاً اشتباهاً لیست خدمات برمی‌گشت)
    path('business-categories/', BusinessCategoryListView.as_view(), name='business-category-list'),
]