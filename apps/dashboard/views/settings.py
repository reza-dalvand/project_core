# apps/dashboard/views/settings.py
"""
مدیریت تنظیمات داشبورد — نقش‌ها، ادمین‌ها، سیستم، پیامک، لندینگ
✅ فاز ۵: افزودن Audit Log + Cache
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from apps.core.models import AppConfig
from apps.notifications.models import SMSTemplate
from apps.landing.models import SiteSettings
from apps.dashboard.models import AdminRole, AdminUser
from apps.dashboard.decorators import admin_login_required, role_required
from apps.dashboard.services.cache_service import DashboardCacheService
from apps.dashboard.services.audit_service import DashboardAuditService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#   داشبورد تنظیمات
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def settings_index_view(request):
    """داشبورد اصلی تنظیمات"""
    # ✅ فاز ۵: کش نقش‌ها
    role_stats = DashboardCacheService.get_admin_roles()
    if role_stats is None:
        role_stats = AdminRole.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )
        DashboardCacheService.set_admin_roles(role_stats)

    # ✅ فاز ۵: کش آمار ادمین‌ها
    admin_stats = DashboardCacheService.get_admin_stats()
    if admin_stats is None:
        admin_stats = AdminUser.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )
        DashboardCacheService.set_admin_stats(admin_stats)

    # ✅ فاز ۵: کش تنظیمات سیستم
    app_config = DashboardCacheService.get_system_settings()
    if app_config is None:
        app_config = AppConfig.objects.first()
        DashboardCacheService.set_system_settings(app_config)

    # ✅ فاز ۵: کش قالب‌های پیامک
    sms_stats = DashboardCacheService.get_sms_templates()
    if sms_stats is None:
        sms_stats = SMSTemplate.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )
        DashboardCacheService.set_sms_templates(sms_stats)

    # ✅ فاز ۵: کش تنظیمات لندینگ
    site_settings = DashboardCacheService.get_landing_settings()
    if site_settings is None:
        site_settings = SiteSettings.objects.first()
        DashboardCacheService.set_landing_settings(site_settings)

    context = {
        'role_stats': role_stats,
        'admin_stats': admin_stats,
        'app_config': app_config,
        'sms_stats': sms_stats,
        'site_settings': site_settings,
    }
    return render(request, 'dashboard/settings/index.html', context)


# ═══════════════════════════════════════════════
#   نقش‌ها
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def roles_list_view(request):
    """لیست نقش‌های ادمین"""
    roles = AdminRole.objects.filter(is_active=True).annotate(
        admins_count=Count('admins', filter=Q(admins__is_active=True))
    ).order_by('name')
    context = {
        'roles': roles,
    }
    return render(request, 'dashboard/settings/roles_list.html', context)


@role_required('super_admin')
@admin_login_required
def role_create_view(request):
    """ایجاد نقش جدید"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        permissions = request.POST.getlist('permissions')

        if not name:
            messages.error(request, 'نام نقش الزامی است.')
            return redirect(reverse('dashboard:role_create'))

        if AdminRole.objects.filter(name=name).exists():
            messages.error(request, 'این نقش قبلاً ایجاد شده است.')
            return redirect(reverse('dashboard:role_create'))

        role = AdminRole.objects.create(
            name=name,
            description=description,
            permissions=permissions,
        )

        # ✅ فاز ۵: بی‌اعتبار کردن کش نقش‌ها
        DashboardCacheService.invalidate_admin_roles()

        # ✅ فاز ۵: ثبت در Audit Log
        DashboardAuditService.log_role_created(request, role)

        messages.success(request, f'نقش "{role.get_name_display()}" با موفقیت ایجاد شد.')
        return redirect(reverse('dashboard:roles_list'))

    available_permissions = [
        ('users', '👥 کاربران'),
        ('businesses', '🏪 کسب‌وکارها'),
        ('financial', '💰 مالی'),
        ('content', '📋 محتوا'),
        ('support', '🎧 پشتیبانی'),
        ('settings', '⚙️ تنظیمات'),
    ]
    context = {
        'available_permissions': available_permissions,
    }
    return render(request, 'dashboard/settings/role_create.html', context)


@role_required('super_admin')
@admin_login_required
def role_edit_view(request, role_id):
    """ویرایش نقش"""
    role = get_object_or_404(AdminRole, id=role_id)

    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        permissions = request.POST.getlist('permissions')
        is_active = request.POST.get('is_active') == 'on'

        role.description = description
        role.permissions = permissions
        role.is_active = is_active
        role.save()

        # ✅ فاز ۵: بی‌اعتبار کردن کش نقش‌ها
        DashboardCacheService.invalidate_admin_roles()

        # ✅ فاز ۵: ثبت در Audit Log
        DashboardAuditService.log(
            request=request,
            action=DashboardAuditService.Action.ROLE_EDITED,
            target_type='role',
            target_id=role.id,
            target_name=role.get_name_display(),
            details={'permissions': permissions, 'is_active': is_active},
            severity='warning',
        )

        messages.success(request, f'نقش "{role.get_name_display()}" بروزرسانی شد.')
        return redirect(reverse('dashboard:roles_list'))

    available_permissions = [
        ('users', '👥 کاربران'),
        ('businesses', '🏪 کسب‌وکارها'),
        ('financial', '💰 مالی'),
        ('content', '📋 محتوا'),
        ('support', '🎧 پشتیبانی'),
        ('settings', '⚙️ تنظیمات'),
    ]
    context = {
        'role': role,
        'available_permissions': available_permissions,
    }
    return render(request, 'dashboard/settings/role_edit.html', context)


@role_required('super_admin')
@admin_login_required
def role_delete_view(request, role_id):
    """حذف نقش"""
    role = get_object_or_404(AdminRole, id=role_id)

    if request.method == 'POST':
        if role.admins.exists():
            messages.error(request, 'این نقش دارای ادمین است و قابل حذف نیست.')
        else:
            # ✅ فاز ۵: ثبت در Audit Log قبل از حذف
            DashboardAuditService.log_role_deleted(request, role)

            role.delete()

            # ✅ فاز ۵: بی‌اعتبار کردن کش نقش‌ها
            DashboardCacheService.invalidate_admin_roles()

            messages.success(request, f'نقش "{role.get_name_display()}" حذف شد.')
        return redirect(reverse('dashboard:roles_list'))


# ═══════════════════════════════════════════════
#   ادمین‌ها
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def admins_list_view(request):
    """لیست ادمین‌ها"""
    search = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)

    queryset = AdminUser.objects.filter(is_active=True).select_related(
        'user', 'role'
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(user__phone__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    # ✅ فاز ۵: کش آمار ادمین‌ها
    stats = DashboardCacheService.get_admin_stats()
    if stats is None:
        stats = {
            'total': AdminUser.objects.count(),
            'active': AdminUser.objects.filter(is_active=True).count(),
        }
        DashboardCacheService.set_admin_stats(stats)

    context = {
        'page_obj': page_obj,
        'search': search,
        'stats': stats,
    }
    return render(request, 'dashboard/settings/admins_list.html', context)


@role_required('super_admin')
@admin_login_required
def admin_create_view(request):
    """افزودن ادمین جدید"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        role_id = request.POST.get('role')

        if not phone:
            messages.error(request, 'شماره تلفن الزامی است.')
            return redirect(reverse('dashboard:admin_create'))

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            messages.error(request, 'کاربری با این شماره تلفن یافت نشد.')
            return redirect(reverse('dashboard:admin_create'))

        if AdminUser.objects.filter(user=user).exists():
            messages.error(request, 'این کاربر قبلاً ادمین است.')
            return redirect(reverse('dashboard:admin_create'))

        role = None
        if role_id:
            role = AdminRole.objects.filter(id=role_id).first()

        admin_user = AdminUser.objects.create(
            user=user,
            role=role,
            is_active=True,
        )

        user.is_staff = True
        user.save(update_fields=['is_staff'])

        # ✅ فاز ۵: بی‌اعتبار کردن کش آمار ادمین‌ها
        DashboardCacheService.invalidate_admin_stats()

        # ✅ فاز ۵: ثبت در Audit Log
        role_name = role.get_name_display() if role else 'بدون نقش'
        DashboardAuditService.log_admin_created(request, admin_user, role_name)

        messages.success(request, f'کاربر {phone} به عنوان ادمین اضافه شد.')
        return redirect(reverse('dashboard:admins_list'))

    roles = AdminRole.objects.filter(is_active=True)
    context = {
        'roles': roles,
    }
    return render(request, 'dashboard/settings/admin_create.html', context)


@role_required('super_admin')
@admin_login_required
def admin_toggle_active_view(request, admin_id):
    """فعال/غیرفعال کردن ادمین"""
    admin_user = get_object_or_404(AdminUser, id=admin_id)

    if request.method == 'POST':
        current_phone = request.session.get('dashboard_admin_phone')
        if admin_user.user.phone == current_phone:
            messages.error(request, 'نمی‌توانید حساب خودتان را غیرفعال کنید.')
        else:
            admin_user.is_active = not admin_user.is_active
            admin_user.save(update_fields=['is_active'])

            # ✅ فاز ۵: بی‌اعتبار کردن کش آمار ادمین‌ها
            DashboardCacheService.invalidate_admin_stats()

            # ✅ فاز ۵: ثبت در Audit Log
            DashboardAuditService.log_admin_toggled(
                request, admin_user, admin_user.is_active
            )

            status_text = 'فعال' if admin_user.is_active else 'غیرفعال'
            messages.success(request, f'ادمین {admin_user.user.phone} {status_text} شد.')
        return redirect(reverse('dashboard:admins_list'))


@role_required('super_admin')
@admin_login_required
def admin_delete_view(request, admin_id):
    """حذف ادمین"""
    admin_user = get_object_or_404(AdminUser, id=admin_id)

    if request.method == 'POST':
        current_phone = request.session.get('dashboard_admin_phone')
        if admin_user.user.phone == current_phone:
            messages.error(request, 'نمی‌توانید حساب خودتان را حذف کنید.')
        else:
            phone = admin_user.user.phone

            # ✅ فاز ۵: ثبت در Audit Log قبل از حذف
            DashboardAuditService.log_admin_deleted(request, admin_user)

            admin_user.delete()

            # ✅ فاز ۵: بی‌اعتبار کردن کش آمار ادمین‌ها
            DashboardCacheService.invalidate_admin_stats()

            messages.success(request, f'ادمین {phone} حذف شد.')
        return redirect(reverse('dashboard:admins_list'))


# ═══════════════════════════════════════════════
#   تنظیمات سیستم
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def system_settings_view(request):
    """تنظیمات سیستم (نسخه، حالت تعمیرات)"""
    config = AppConfig.objects.first()

    if request.method == 'POST':
        if not config:
            config = AppConfig()

        config.latest_version = request.POST.get('latest_version', config.latest_version)
        config.min_required_version = request.POST.get('min_required_version', config.min_required_version)
        config.is_force_update = request.POST.get('is_force_update') == 'on'
        config.update_title = request.POST.get('update_title', config.update_title)
        config.update_message = request.POST.get('update_message', config.update_message)
        config.is_maintenance = request.POST.get('is_maintenance') == 'on'
        config.maintenance_title = request.POST.get('maintenance_title', config.maintenance_title)
        config.maintenance_message = request.POST.get('maintenance_message', config.maintenance_message)
        config.maintenance_estimated_end = request.POST.get('maintenance_estimated_end', config.maintenance_estimated_end)
        config.maintenance_reason = request.POST.get('maintenance_reason', config.maintenance_reason)
        config.support_phone = request.POST.get('support_phone', config.support_phone)
        config.save()

        # ✅ فاز ۵: بی‌اعتبار کردن کش تنظیمات سیستم
        DashboardCacheService.invalidate_system_settings()

        # ✅ فاز ۵: ثبت در Audit Log
        DashboardAuditService.log_system_settings_updated(request, config)

        messages.success(request, 'تنظیمات سیستم بروزرسانی شد.')
        return redirect(reverse('dashboard:system_settings'))

    context = {
        'config': config,
    }
    return render(request, 'dashboard/settings/system_settings.html', context)


# ═══════════════════════════════════════════════
#   قالب‌های پیامک
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def sms_templates_view(request):
    """لیست قالب‌های پیامک"""
    templates = SMSTemplate.objects.filter(is_active=True).order_by('type')
    context = {
        'templates': templates,
    }
    return render(request, 'dashboard/settings/sms_templates.html', context)


@role_required('super_admin')
@admin_login_required
def sms_template_edit_view(request, template_id):
    """ویرایش قالب پیامک"""
    template = get_object_or_404(SMSTemplate, id=template_id)

    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.pattern = request.POST.get('pattern', template.pattern)
        template.is_active = request.POST.get('is_active') == 'on'
        template.save()

        # ✅ فاز ۵: بی‌اعتبار کردن کش قالب‌ها
        DashboardCacheService.invalidate_sms_templates()

        # ✅ فاز ۵: ثبت در Audit Log
        DashboardAuditService.log_sms_template_edited(request, template)

        messages.success(request, f'قالب "{template.name}" بروزرسانی شد.')
        return redirect(reverse('dashboard:sms_templates'))

    context = {
        'template': template,
    }
    return render(request, 'dashboard/settings/sms_template_edit.html', context)


# ═══════════════════════════════════════════════
#   تنظیمات لندینگ
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def landing_settings_view(request):
    """تنظیمات لندینگ"""
    settings_obj = SiteSettings.objects.first()

    if request.method == 'POST':
        if not settings_obj:
            settings_obj = SiteSettings()

        fields = [
            'site_name', 'site_slogan', 'phone', 'email',
            'address', 'working_hours',
            'instagram_url', 'telegram_url', 'whatsapp_url',
            'twitter_url', 'cafebazaar_url', 'myket_url',
            'google_play_url', 'app_store_url',
            'footer_text', 'copyright_year',
            'meta_description', 'meta_keywords',
        ]
        for field in fields:
            value = request.POST.get(field)
            if value is not None:
                setattr(settings_obj, field, value)
        settings_obj.save()

        # ✅ فاز ۵: بی‌اعتبار کردن کش تنظیمات لندینگ
        DashboardCacheService.invalidate_landing_settings()

        # ✅ فاز ۵: ثبت در Audit Log
        DashboardAuditService.log_landing_settings_updated(request)

        messages.success(request, 'تنظیمات لندینگ بروزرسانی شد.')
        return redirect(reverse('dashboard:landing_settings'))

    context = {'settings': settings_obj}
    return render(request, 'dashboard/settings/landing_settings.html', context)