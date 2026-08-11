"""
URL Configuration برای اپ landing
"""
from django.urls import path
from . import views

app_name = 'landing'

urlpatterns = [
    # صفحه اصلی سایت معرفی
    path('', views.index, name='index'),

    # API برای ارسال فرم تماس
    path('api/contact/', views.submit_contact, name='submit_contact'),
]