"""
Permission های سفارشی برای DRF — بدون نقش (role)
هر کاربر می‌تواند یک کسب‌وکار داشته باشد
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """صاحب آبجکت یا فقط خواندنی"""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

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

        # دریافت کسب‌وکار کاربر
        user_business = request.user.businesses.filter(is_active=True).first()
        if not user_business:
            return False

        # بررسی مالکیت
        if hasattr(obj, 'business'):
            return obj.business == user_business
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if obj == user_business:
            return True
        return False


class IsApprovedBusinessOwner(permissions.BasePermission):
    """کاربری که کسب‌وکار تایید شده دارد"""
    message = 'کسب‌وکار شما هنوز تایید نشده است'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        business = request.user.businesses.filter(
            is_active=True,
            status='approved',
        ).first()
        return business is not None


class AllowAnyVerified(permissions.BasePermission):
    """کاربران تایید شده (شماره موبایل)"""
    message = 'لطفاً ابتدا شماره موبایل خود را تایید کنید'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_verified
        )