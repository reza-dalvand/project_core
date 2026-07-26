"""
URL configuration for accounts app (API endpoints)
"""
from django.urls import path

app_name = 'accounts'

urlpatterns = [
    # بعداً API های احراز هویت اینجا اضافه میشن
    # path('login/', views.login, name='login'),
    # path('otp/verify/', views.verify_otp, name='verify_otp'),
    # path('profile/', views.profile, name='profile'),
]