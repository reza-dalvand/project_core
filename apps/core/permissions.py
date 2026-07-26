"""
Permission های سفارشی برای DRF
"""
from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    """فقط کاربران عادی (مشتری)"""

    def has_permission(self, request, view):
        return (
                request.user
                and request.user.is_authenticated
                and request.user.role in ['customer', 'business_owner']
        )


class IsBusinessOwner(permissions.BasePermission):
    """فقط صاحبان کسب‌وکار"""

    def has_permission(self, request, view):
        return (
                request.user
                and request.user.is_authenticated
                and request.user.role == 'business_owner'
        )


class IsStaff(permissions.BasePermission):
    """فقط کارمندان اپ (پشتیبان و ادمین)"""

    def has_permission(self, request, view):
        return (
                request.user
                and request.user.is_authenticated
                and request.user.role in ['super_admin', 'app_admin', 'app_staff', 'support']
        )


class IsAdmin(permissions.BasePermission):
    """فقط ادمین‌ها"""

    def has_permission(self, request, view):
        return (
                request.user
                and request.user.is_authenticated
                and request.user.role in ['super_admin', 'app_admin']
        )


class IsSuperAdmin(permissions.BasePermission):
    """فقط مدیر ارشد"""

    def has_permission(self, request, view):
        return (
                request.user
                and request.user.is_authenticated
                and request.user.role == 'super_admin'
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """صاحب آبجکت یا فقط خواندنی"""

    def has_object_permission(self, request, view, obj):
        # خواندنی برای همه
        if request.method in permissions.SAFE_METHODS:
            return True

        # نوشتنی فقط برای صاحب آبجکت
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'business') and hasattr(obj.business, 'owner'):
            return obj.business.owner == request.user

        return False