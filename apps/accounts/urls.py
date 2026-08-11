"""
URL configuration for accounts app — بدون role
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from .views.auth import (
    SendOTPView,
    VerifyOTPView,
    CustomTokenRefreshView,
    LogoutView,
    NationalIdVerificationView,
    UserDeviceListView,
    RevokeDeviceView,
    DeleteAccountView,
)
from .views.profile import (
    ProfileView,
    ChangePhoneRequestView,
    ChangePhoneConfirmView,
)

app_name = 'accounts'

urlpatterns = [
    # ═══════════ Authentication ═══════════
    path('auth/otp/send/', SendOTPView.as_view(), name='otp-send'),
    path('auth/otp/verify/', VerifyOTPView.as_view(), name='otp-verify'),
    path('auth/token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # ═══════════ National ID ═══════════
    path('auth/national-id/verify/', NationalIdVerificationView.as_view(), name='national-id-verify'),

    # ═══════════ Profile ═══════════
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/change-phone/', ChangePhoneRequestView.as_view(), name='change-phone-request'),
    path('profile/change-phone/confirm/', ChangePhoneConfirmView.as_view(), name='change-phone-confirm'),

    # ═══════════ Devices ═══════════
    path('devices/', UserDeviceListView.as_view(), name='device-list'),
    path('devices/<int:device_id>/revoke/', RevokeDeviceView.as_view(), name='device-revoke'),

    # ═══════════ Account ═══════════
    path('account/delete/', DeleteAccountView.as_view(), name='delete-account'),
]