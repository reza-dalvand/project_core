"""
Mixin های کنترل دسترسی به Admin بر اساس نقش کاربر
"""
from functools import wraps


class RoleBasedAdminMixin:
    """
    Mixin پایه برای کنترل دسترسی به ModelAdmin بر اساس نقش کاربر

    استفاده:
        class MyModelAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
            allowed_roles = ['super_admin', 'app_admin']
    """

    # نقش‌هایی که به این مدل دسترسی دارند
    # خالی = همه نقش‌های staff دسترسی دارند
    allowed_roles = []

    # آیا فقط مشاهده (view) مجاز است؟ (بدون تغییر)
    view_only_roles = []

    def _has_role_access(self, request, require_change=False):
        """بررسی دسترسی کاربر بر اساس نقش"""
        user = request.user

        if not user.is_authenticated:
            return False

        # Superuser همیشه دسترسی کامل دارد
        if user.is_superuser:
            return True

        # Staff نباشد دسترسی ندارد
        if not user.is_staff:
            return False

        # اگر allowed_roles خالی باشد، همه staff دسترسی دارند
        if not self.allowed_roles:
            return True if not require_change else user.has_module_perms(self.model._meta.app_label)

        # بررسی نقش کاربر
        user_role = getattr(user, 'role', None)

        if user_role in self.allowed_roles:
            return True

        # برای عملیات تغییر، view_only_roles اجازه نمی‌دهند
        if require_change and user_role in self.view_only_roles:
            return False

        if not require_change and user_role in self.view_only_roles:
            return True

        return False

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

        if user.is_superuser or user.role in ['super_admin', 'app_admin']:
            return qs

        # برای business_owner فقط داده‌های خودشان
        if user.role == 'business_owner' and hasattr(user, 'business'):
            if hasattr(self.model, 'business'):
                return qs.filter(business=user.business)
            elif hasattr(self.model, 'owner'):
                return qs.filter(owner=user)

        return qs.none()