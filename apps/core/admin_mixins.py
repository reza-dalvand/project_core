"""
Mixin های کنترل دسترسی به Admin بر اساس نقش کاربر
نسخه بدون role — هر کاربر می‌تواند یک کسب‌وکار داشته باشد
"""
from functools import wraps


class RoleBasedAdminMixin:
    """
    Mixin پایه برای کنترل دسترسی به ModelAdmin بر اساس نقش کاربر
    در سیستم بدون role، همه staff ها دسترسی دارند
    """
    allowed_roles = []
    view_only_roles = []

    def _has_role_access(self, request, require_change=False):
        """بررسی دسترسی کاربر — بدون نقش (role)"""
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not user.is_staff:
            return False
        # در سیستم بدون role، همه staff ها دسترسی دارند
        return True

    def has_module_permission(self, request):
        """آیا این ماژول در منوی admin نمایش داده شود؟"""
        return self._has_role_access(request)

    def has_view_permission(self, request, obj=None):
        """آیا کاربر می‌تواند مشاهده کند؟"""
        return self._has_role_access(request, require_change=False)

    def has_add_permission(self, request):
        """آیا کاربر می‌تواند اضافه کند؟"""
        if not self._has_role_access(request, require_change=True):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """آیا کاربر می‌تواند ویرایش کند؟"""
        if not self._has_role_access(request, require_change=True):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """آیا کاربر می‌تواند حذف کند؟"""
        if not self._has_role_access(request, require_change=True):
            return False
        return super().has_delete_permission(request, obj)


class LandingAdminMixin(RoleBasedAdminMixin):
    """مخصوص مدل‌های سایت معرفی (Landing)"""
    allowed_roles = ['super_admin', 'landing_admin']


class AppAdminMixin(RoleBasedAdminMixin):
    """مخصوص مدل‌های بک‌اند اپلیکیشن (Admin کامل)"""
    allowed_roles = ['super_admin', 'app_admin']


class AppStaffMixin(RoleBasedAdminMixin):
    """مخصوص کارمندان اپ (فقط مشاهده + عملیات محدود)"""
    allowed_roles = ['super_admin', 'app_admin', 'app_staff']
    view_only_roles = ['app_staff']


class BusinessOwnerMixin(RoleBasedAdminMixin):
    """مخصوص صاحبان کسب و کار - فقط داده‌های خودشان"""
    allowed_roles = ['super_admin', 'app_admin', 'business_owner']

    def get_queryset(self, request):
        """فیلتر کوئری‌ست - فقط داده‌های مربوط به خود کاربر"""
        qs = super().get_queryset(request)
        user = request.user

        # سوپر یوزر و ادمین‌ها به همه چیز دسترسی دارند
        if user.is_superuser or user.is_staff:
            return qs

        # برای صاحب کسب‌وکار: فقط داده‌های کسب‌وکار خودش
        user_business = user.businesses.filter(is_active=True).first()
        if user_business:
            if hasattr(self.model, 'business'):
                return qs.filter(business=user_business)
            elif hasattr(self.model, 'owner'):
                return qs.filter(owner=user)

        return qs.none()