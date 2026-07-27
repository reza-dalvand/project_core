"""
Permission های سفارشی برای DRF
"""
from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    """فقط مشتریان"""
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


class IsApprovedBusinessOwner(permissions.BasePermission):
    """صاحب کسب‌وکاری که تایید شده است"""
    message = 'کسب‌وکار شما هنوز تایید نشده است'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role != 'business_owner':
            return False
        return hasattr(request.user, 'business') and request.user.business.status == 'approved'


class IsStaff(permissions.BasePermission):
    """کارمندان اپ (پشتیبان و ادمین)"""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ['super_admin', 'app_admin', 'app_staff']
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
        if request.method in permissions.SAFE_METHODS:
            return True

        # بررسی مالکیت
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'customer'):
            return obj.customer == request.user
        if hasattr(obj, 'business') and hasattr(obj.business, 'owner'):
            return obj.business.owner == request.user
        return False


class IsBusinessOwnerOfObject(permissions.BasePermission):
    """فقط صاحب کسب‌وکاری که مالک آبجکت است"""
    message = 'شما فقط به کسب‌وکار خود دسترسی دارید'

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.role != 'business_owner':
            return False
        if not hasattr(request.user, 'business'):
            return False

        # بررسی مالکیت
        if hasattr(obj, 'business'):
            return obj.business == request.user.business
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if obj == request.user.business:
            return True
        return False


class AllowAnyVerified(permissions.BasePermission):
    """کاربران تایید شده (شماره موبایل)"""
    message = 'لطفاً ابتدا شماره موبایل خود را تایید کنید'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_verified
        )