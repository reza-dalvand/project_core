# apps/dashboard/views/settings.py
"""
مدیریت تنظیمات داشبورد — نقش‌ها، ادمین‌ها، سیستم، پیامک، لندینگ
✅ فاز ۳: رفع ۴ باگ
- ۳.۶.۱: اعتبارسنجی فرمت نسخه (semver)
- ۳.۶.۲: هندل خطای آپلود فایل در لندینگ
- ۳.۶.۳: بررسی تکراری نبودن provider_template_id
- ۳.۶.۴: اعتبارسنجی بهتر در landing_items_view
"""
import json
import logging
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from apps.core.models import AppConfig
from apps.notifications.models import SMSTemplate
from apps.landing.models import (
    SiteSettings, NavItem, FooterLinkGroup, FooterLink, TrustBadge,
)
from apps.dashboard.models import AdminRole, AdminUser
from apps.dashboard.decorators import admin_login_required, role_required
from apps.dashboard.services.cache_service import DashboardCacheService
from apps.dashboard.services.audit_service import DashboardAuditService

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۶.۱: اعتبارسنجی فرمت نسخه (semver)
# ═══════════════════════════════════════════════
SEMVER_PATTERN = re.compile(
    r'^\d+\.\d+\.\d+$'
)


def validate_semver(version_str):
    """اعتبارسنجی فرمت نسخه semver (مثلاً 1.2.3)"""
    if not version_str:
        return False
    return bool(SEMVER_PATTERN.match(version_str.strip()))


# ═══════════════════════════════════════════════
#   داشبورد تنظیمات
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def settings_index_view(request):
    """داشبورد اصلی تنظیمات"""
    role_stats = DashboardCacheService.get_admin_roles()
    if role_stats is None:
        role_stats = AdminRole.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )
        DashboardCacheService.set_admin_roles(role_stats)

    admin_stats = DashboardCacheService.get_admin_stats()
    if admin_stats is None:
        admin_stats = AdminUser.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )
        DashboardCacheService.set_admin_stats(admin_stats)

    app_config = DashboardCacheService.get_system_settings()
    if app_config is None:
        app_config = AppConfig.objects.first()
        DashboardCacheService.set_system_settings(app_config)

    sms_stats = DashboardCacheService.get_sms_templates()
    if sms_stats is None:
        sms_stats = SMSTemplate.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )
        DashboardCacheService.set_sms_templates(sms_stats)

    site_settings = DashboardCacheService.get_landing_settings()
    if site_settings is None:
        site_settings = SiteSettings.objects.first()
        DashboardCacheService.set_landing_settings(site_settings)

    try:
        landing_items_stats = {
            'nav_items': NavItem.objects.count(),
            'footer_links': FooterLink.objects.count(),
            'trust_badges': TrustBadge.objects.count(),
        }
    except Exception:
        landing_items_stats = {
            'nav_items': 0,
            'footer_links': 0,
            'trust_badges': 0,
        }

    context = {
        'role_stats': role_stats,
        'admin_stats': admin_stats,
        'app_config': app_config,
        'sms_stats': sms_stats,
        'site_settings': site_settings,
        'landing_items_stats': landing_items_stats,
    }
    return render(request, 'dashboard/settings/index.html', context)


# ═══════════════════════════════════════════════
#   نقش‌ها
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def roles_list_view(request):
    """لیست نقش‌های ادمین"""
    page_number = request.GET.get('page', 1)
    queryset = AdminRole.objects.filter(is_active=True).annotate(
        admins_count=Count('admins', filter=Q(admins__is_active=True))
    ).order_by('name')

    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'roles': page_obj,
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
            name=name, description=description, permissions=permissions,
        )
        DashboardCacheService.invalidate_admin_roles()
        DashboardAuditService.log_role_created(request, role)
        messages.success(request, f'نقش "{role.get_name_display()}" ایجاد شد.')
        return redirect(reverse('dashboard:roles_list'))

    available_permissions = [
        ('users', '👥 کاربران'),
        ('businesses', '🏪 کسب‌وکارها'),
        ('financial', '💰 مالی'),
        ('content', '📋 محتوا'),
        ('support', '🎧 پشتیبانی'),
        ('settings', '⚙️ تنظیمات'),
    ]
    context = {'available_permissions': available_permissions}
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

        DashboardCacheService.invalidate_admin_roles()
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
    context = {'role': role, 'available_permissions': available_permissions}
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
            DashboardAuditService.log_role_deleted(request, role)
            role.delete()
            DashboardCacheService.invalidate_admin_roles()
            messages.success(request, f'نقش "{role.get_name_display()}" حذف شد.')
        return redirect(reverse('dashboard:roles_list'))

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

    stats = DashboardCacheService.get_admin_stats()
    if stats is None:
        stats = {
            'total': AdminUser.objects.count(),
            'active': AdminUser.objects.filter(is_active=True).count(),
        }
        DashboardCacheService.set_admin_stats(stats)

    context = {'page_obj': page_obj, 'search': search, 'stats': stats}
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
            user=user, role=role, is_active=True,
        )
        user.is_staff = True
        user.save(update_fields=['is_staff'])

        DashboardCacheService.invalidate_admin_stats()
        role_name = role.get_name_display() if role else 'بدون نقش'
        DashboardAuditService.log_admin_created(request, admin_user, role_name)
        messages.success(request, f'کاربر {phone} به عنوان ادمین اضافه شد.')
        return redirect(reverse('dashboard:admins_list'))

    roles = AdminRole.objects.filter(is_active=True)
    context = {'roles': roles}
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
            DashboardCacheService.invalidate_admin_stats()
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
            DashboardAuditService.log_admin_deleted(request, admin_user)
            admin_user.delete()
            DashboardCacheService.invalidate_admin_stats()
            messages.success(request, f'ادمین {phone} حذف شد.')

    return redirect(reverse('dashboard:admins_list'))


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۶.۱: تنظیمات سیستم با اعتبارسنجی نسخه
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def system_settings_view(request):
    """تنظیمات سیستم — نسخه، تعمیرات، فروشگاه، چنج‌لاگ"""
    config = AppConfig.objects.first()

    if request.method == 'POST':
        if not config:
            config = AppConfig()

        # ─── ✅ FIX ۳.۶.۱: اعتبارسنجی فرمت نسخه ───
        latest_version = request.POST.get(
            'latest_version', config.latest_version
        ).strip()
        min_required_version = request.POST.get(
            'min_required_version', config.min_required_version
        ).strip()

        if not validate_semver(latest_version):
            messages.error(
                request,
                'فرمت "آخرین نسخه" نامعتبر است. '
                'فرمت صحیح: 1.2.3 (مثلاً 2.1.0)'
            )
            return redirect(reverse('dashboard:system_settings'))

        if not validate_semver(min_required_version):
            messages.error(
                request,
                'فرمت "حداقل نسخه مورد نیاز" نامعتبر است. '
                'فرمت صحیح: 1.2.3 (مثلاً 1.0.0)'
            )
            return redirect(reverse('dashboard:system_settings'))

        config.latest_version = latest_version
        config.min_required_version = min_required_version
        config.is_force_update = request.POST.get('is_force_update') == 'on'
        config.update_title = request.POST.get(
            'update_title', config.update_title
        )
        config.update_message = request.POST.get(
            'update_message', config.update_message
        )

        # ─── فروشگاه ───
        config.store_url = request.POST.get('store_url', config.store_url)
        config.store_name = request.POST.get('store_name', config.store_name)

        # ─── چنج‌لاگ ───
        changelog_raw = request.POST.get('changelog', '').strip()
        if changelog_raw:
            try:
                changelog_data = json.loads(changelog_raw)
                if isinstance(changelog_data, list):
                    config.changelog = changelog_data
                else:
                    messages.warning(
                        request,
                        'چنج‌لاگ باید یک آرایه JSON باشد '
                        'مثال: [{"icon": "✨", "text": "بهبود"}]'
                    )
            except json.JSONDecodeError:
                messages.warning(
                    request,
                    'فرمت JSON چنج‌لاگ نامعتبر است. تغییر ذخیره نشد.'
                )
        else:
            config.changelog = []

        # ─── حالت تعمیرات ───
        config.is_maintenance = request.POST.get('is_maintenance') == 'on'
        config.maintenance_title = request.POST.get(
            'maintenance_title', config.maintenance_title
        )
        config.maintenance_message = request.POST.get(
            'maintenance_message', config.maintenance_message
        )
        config.maintenance_estimated_end = request.POST.get(
            'maintenance_estimated_end', config.maintenance_estimated_end
        )
        config.maintenance_reason = request.POST.get(
            'maintenance_reason', config.maintenance_reason
        )
        config.support_phone = request.POST.get(
            'support_phone', config.support_phone
        )

        config.save()
        DashboardCacheService.invalidate_system_settings()
        DashboardAuditService.log_system_settings_updated(request, config)
        messages.success(request, 'تنظیمات سیستم بروزرسانی شد.')
        return redirect(reverse('dashboard:system_settings'))

    changelog_json = ''
    if config and config.changelog:
        changelog_json = json.dumps(config.changelog, ensure_ascii=False, indent=2)

    context = {
        'config': config,
        'changelog_json': changelog_json,
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
    context = {'templates': templates}
    return render(request, 'dashboard/settings/sms_templates.html', context)


# ✅ FIX ۳.۶.۳: ایجاد قالب با بررسی تکراری نبودن
@role_required('super_admin')
@admin_login_required
def sms_template_create_view(request):
    """ایجاد قالب پیامک جدید"""
    if request.method == 'POST':
        template_type = request.POST.get('type', '').strip()
        name = request.POST.get('name', '').strip()
        provider_template_id = request.POST.get('provider_template_id', '').strip()
        pattern = request.POST.get('pattern', '').strip()
        variables_raw = request.POST.get('variables', '').strip()
        send_method = request.POST.get('send_method', 'simple').strip()

        # ─── اعتبارسنجی ───
        if not template_type:
            messages.error(request, 'نوع قالب الزامی است.')
            return redirect(reverse('dashboard:sms_template_create'))

        if template_type not in dict(SMSTemplate.Type.choices):
            messages.error(request, 'نوع قالب نامعتبر است.')
            return redirect(reverse('dashboard:sms_template_create'))

        if SMSTemplate.objects.filter(type=template_type).exists():
            messages.error(request, 'این نوع قالب قبلاً ایجاد شده است.')
            return redirect(reverse('dashboard:sms_template_create'))

        if not name or len(name) < 3:
            messages.error(request, 'نام قالب باید حداقل ۳ کاراکتر باشد.')
            return redirect(reverse('dashboard:sms_template_create'))

        if not provider_template_id:
            messages.error(request, 'شناسه قالب در سرویس‌دهنده الزامی است.')
            return redirect(reverse('dashboard:sms_template_create'))

        # ✅ FIX ۳.۶.۳: بررسی تکراری نبودن provider_template_id
        if SMSTemplate.objects.filter(
            provider_template_id=provider_template_id
        ).exists():
            messages.error(
                request,
                f'شناسه قالب "{provider_template_id}" قبلاً '
                f'برای قالب دیگری استفاده شده است.'
            )
            return redirect(reverse('dashboard:sms_template_create'))

        if not pattern or len(pattern) < 5:
            messages.error(request, 'متن قالب باید حداقل ۵ کاراکتر باشد.')
            return redirect(reverse('dashboard:sms_template_create'))

        if send_method not in dict(SMSTemplate.SendMethod.choices):
            messages.error(request, 'روش ارسال نامعتبر است.')
            return redirect(reverse('dashboard:sms_template_create'))

        # ─── پارس متغیرها ───
        variables = []
        if variables_raw:
            variables = [
                v.strip() for v in variables_raw.split(',')
                if v.strip()
            ]

        try:
            template = SMSTemplate.objects.create(
                type=template_type,
                name=name,
                provider_template_id=provider_template_id,
                pattern=pattern,
                variables=variables,
                send_method=send_method,
                is_active=True,
            )
            DashboardCacheService.invalidate_sms_templates()
            DashboardAuditService.log_sms_template_edited(request, template)
            messages.success(request, f'قالب "{name}" ایجاد شد.')
            return redirect(reverse('dashboard:sms_templates'))
        except Exception as e:
            logger.error(f"SMS template create error: {e}", exc_info=True)
            messages.error(request, 'خطا در ایجاد قالب پیامک.')

    context = {
        'type_choices': SMSTemplate.Type.choices,
        'send_method_choices': SMSTemplate.SendMethod.choices,
    }
    return render(request, 'dashboard/settings/sms_template_create.html', context)


@role_required('super_admin')
@admin_login_required
def sms_template_edit_view(request, template_id):
    """ویرایش قالب پیامک"""
    template = get_object_or_404(SMSTemplate, id=template_id)

    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.provider_template_id = request.POST.get(
            'provider_template_id', template.provider_template_id
        )
        template.pattern = request.POST.get('pattern', template.pattern)

        variables_raw = request.POST.get('variables', '').strip()
        if variables_raw:
            template.variables = [
                v.strip() for v in variables_raw.split(',')
                if v.strip()
            ]
        else:
            template.variables = []

        send_method = request.POST.get('send_method', template.send_method)
        if send_method in dict(SMSTemplate.SendMethod.choices):
            template.send_method = send_method

        template.is_active = request.POST.get('is_active') == 'on'
        template.save()

        DashboardCacheService.invalidate_sms_templates()
        DashboardAuditService.log_sms_template_edited(request, template)
        messages.success(request, f'قالب "{template.name}" بروزرسانی شد.')
        return redirect(reverse('dashboard:sms_templates'))

    variables_str = ', '.join(template.variables) if template.variables else ''
    context = {
        'template': template,
        'variables_str': variables_str,
        'send_method_choices': SMSTemplate.SendMethod.choices,
    }
    return render(request, 'dashboard/settings/sms_template_edit.html', context)


@role_required('super_admin')
@admin_login_required
def sms_template_delete_view(request, template_id):
    """حذف قالب پیامک"""
    template = get_object_or_404(SMSTemplate, id=template_id)

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:sms_templates'))

        if template.is_active:
            messages.error(
                request,
                'ابتدا قالب را غیرفعال کنید، سپس حذف کنید.'
            )
            return redirect(reverse('dashboard:sms_templates'))

        if template.logs.exists():
            messages.error(
                request,
                'این قالب دارای لاگ پیامک است و قابل حذف نیست. '
                'فقط می‌توانید آن را غیرفعال کنید.'
            )
            return redirect(reverse('dashboard:sms_templates'))

        try:
            template_name = template.name
            template.delete()
            DashboardCacheService.invalidate_sms_templates()
            DashboardAuditService.log(
                request=request,
                action='settings.sms_template_deleted',
                target_type='sms_template',
                target_id=template_id,
                target_name=template_name,
                severity='warning',
            )
            messages.success(request, f'قالب "{template_name}" حذف شد.')
        except Exception as e:
            logger.error(f"SMS template delete error: {e}", exc_info=True)
            messages.error(request, 'خطا در حذف قالب پیامک.')

    return redirect(reverse('dashboard:sms_templates'))


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۶.۲: تنظیمات لندینگ با هندل خطای آپلود
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def landing_settings_view(request):
    """تنظیمات لندینگ — نسخه کامل با تمام فیلدها"""
    settings_obj = SiteSettings.objects.first()

    if request.method == 'POST':
        if not settings_obj:
            settings_obj = SiteSettings()

        # ─── برندینگ ───
        text_fields = [
            'site_name', 'site_slogan', 'logo_icon',
            'phone', 'email', 'address', 'working_hours',
        ]
        for field in text_fields:
            value = request.POST.get(field)
            if value is not None:
                setattr(settings_obj, field, value)

        # ─── رنگ‌بندی ───
        color_fields = [
            'primary_color', 'primary_dark_color',
            'primary_light_color', 'background_color',
        ]
        for field in color_fields:
            value = request.POST.get(field, '').strip()
            if value:
                if value.startswith('#') and len(value) == 7:
                    setattr(settings_obj, field, value)
                elif value.startswith('#') and len(value) == 4:
                    setattr(settings_obj, field, value)
                else:
                    messages.warning(
                        request,
                        f'رنگ "{field}" باید فرمت #RRGGBB داشته باشد.'
                    )

        # ─── سئو ───
        seo_fields = ['meta_description', 'meta_keywords']
        for field in seo_fields:
            value = request.POST.get(field)
            if value is not None:
                setattr(settings_obj, field, value)

        # ─── لینک‌های دانلود ───
        download_fields = [
            'cafebazaar_url', 'myket_url',
            'google_play_url', 'app_store_url',
        ]
        for field in download_fields:
            value = request.POST.get(field)
            if value is not None:
                setattr(settings_obj, field, value)

        # ─── شبکه‌های اجتماعی ───
        social_fields = [
            'instagram_url', 'telegram_url',
            'whatsapp_url', 'twitter_url',
        ]
        for field in social_fields:
            value = request.POST.get(field)
            if value is not None:
                setattr(settings_obj, field, value)

        # ─── ای‌نماد ───
        enamad_code = request.POST.get('enamad_code')
        if enamad_code is not None:
            settings_obj.enamad_code = enamad_code

        # ─── ✅ FIX ۳.۶.۲: آپلود لوگو و فاویکون با هندل خطا ───
        MAX_IMAGE_SIZE = 5 * 1024 * 1024  # ۵ مگابایت

        logo_file = request.FILES.get('logo')
        if logo_file:
            if logo_file.size > MAX_IMAGE_SIZE:
                messages.error(
                    request,
                    'حجم لوگو نباید بیشتر از ۵ مگابایت باشد.'
                )
            else:
                try:
                    if settings_obj.logo:
                        settings_obj.logo.delete(save=False)
                    settings_obj.logo = logo_file
                except Exception as e:
                    logger.error(f"Logo upload error: {e}")
                    messages.error(request, 'خطا در آپلود لوگو.')

        favicon_file = request.FILES.get('favicon')
        if favicon_file:
            if favicon_file.size > MAX_IMAGE_SIZE:
                messages.error(
                    request,
                    'حجم فاویکون نباید بیشتر از ۵ مگابایت باشد.'
                )
            else:
                try:
                    if settings_obj.favicon:
                        settings_obj.favicon.delete(save=False)
                    settings_obj.favicon = favicon_file
                except Exception as e:
                    logger.error(f"Favicon upload error: {e}")
                    messages.error(request, 'خطا در آپلود فاویکون.')

        enamad_image = request.FILES.get('enamad_image')
        if enamad_image:
            if enamad_image.size > MAX_IMAGE_SIZE:
                messages.error(
                    request,
                    'حجم تصویر ای‌نماد نباید بیشتر از ۵ مگابایت باشد.'
                )
            else:
                try:
                    if settings_obj.enamad_image:
                        settings_obj.enamad_image.delete(save=False)
                    settings_obj.enamad_image = enamad_image
                except Exception as e:
                    logger.error(f"Enamad image upload error: {e}")
                    messages.error(request, 'خطا در آپلود تصویر ای‌نماد.')

        # ─── فوتر ───
        footer_fields = ['footer_text', 'copyright_year']
        for field in footer_fields:
            value = request.POST.get(field)
            if value is not None:
                setattr(settings_obj, field, value)

        settings_obj.save()
        DashboardCacheService.invalidate_landing_settings()
        DashboardAuditService.log_landing_settings_updated(request)
        messages.success(request, 'تنظیمات لندینگ بروزرسانی شد.')
        return redirect(reverse('dashboard:landing_settings'))

    context = {'settings': settings_obj}
    return render(request, 'dashboard/settings/landing_settings.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۶.۴: مدیریت آیتم‌های لندینگ با اعتبارسنجی
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def landing_items_view(request):
    """
    مدیریت آیتم‌های لندینگ:
    - NavItem: آیتم‌های ناوبری
    - FooterLinkGroup + FooterLink: لینک‌های فوتر
    - TrustBadge: نمادهای اعتماد
    """
    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ─── افزودن/ویرایش/حذف آیتم ناوبری ───
        if action == 'add_nav_item':
            label = request.POST.get('label', '').strip()
            anchor = request.POST.get('anchor', '').strip()

            # ✅ FIX ۳.۶.۴: اعتبارسنجی کامل‌تر
            if not label or len(label) < 2:
                messages.error(request, 'عنوان آیتم ناوبری باید حداقل ۲ کاراکتر باشد.')
            elif not anchor or len(anchor) < 2:
                messages.error(request, 'لنگر (anchor) باید حداقل ۲ کاراکتر باشد.')
            elif not anchor.replace('-', '').replace('_', '').isalnum():
                messages.error(
                    request,
                    'لنگر فقط می‌تواند شامل حروف، اعداد، خط تیره و آندرلاین باشد.'
                )
            else:
                NavItem.objects.create(
                    label=label,
                    anchor=anchor,
                    order=NavItem.objects.count(),
                )
                messages.success(request, f'آیتم "{label}" اضافه شد.')

        elif action == 'toggle_nav_item':
            nav_id = request.POST.get('item_id')
            try:
                item = NavItem.objects.get(id=nav_id)
                item.is_active = not item.is_active
                item.save(update_fields=['is_active'])
            except NavItem.DoesNotExist:
                messages.error(request, 'آیتم ناوبری یافت نشد.')

        elif action == 'delete_nav_item':
            nav_id = request.POST.get('item_id')
            deleted, _ = NavItem.objects.filter(id=nav_id).delete()
            if deleted:
                messages.success(request, 'آیتم ناوبری حذف شد.')
            else:
                messages.error(request, 'آیتم ناوبری یافت نشد.')

        # ─── افزودن/حذف لینک فوتر ───
        elif action == 'add_footer_group':
            title = request.POST.get('group_title', '').strip()
            if not title or len(title) < 2:
                messages.error(request, 'عنوان گروه باید حداقل ۲ کاراکتر باشد.')
            else:
                FooterLinkGroup.objects.create(
                    title=title,
                    order=FooterLinkGroup.objects.count(),
                )
                messages.success(request, f'گروه "{title}" اضافه شد.')

        elif action == 'add_footer_link':
            group_id = request.POST.get('group_id')
            label = request.POST.get('link_label', '').strip()
            url = request.POST.get('link_url', '').strip()

            if not label or len(label) < 2:
                messages.error(request, 'عنوان لینک باید حداقل ۲ کاراکتر باشد.')
            elif not url:
                messages.error(request, 'آدرس لینک الزامی است.')
            elif not group_id:
                messages.error(request, 'گروه فوتر الزامی است.')
            else:
                try:
                    group = FooterLinkGroup.objects.get(id=group_id)
                    FooterLink.objects.create(
                        group=group,
                        label=label,
                        url=url,
                        order=group.links.count(),
                    )
                    messages.success(request, f'لینک "{label}" اضافه شد.')
                except FooterLinkGroup.DoesNotExist:
                    messages.error(request, 'گروه یافت نشد.')

        elif action == 'delete_footer_link':
            link_id = request.POST.get('link_id')
            deleted, _ = FooterLink.objects.filter(id=link_id).delete()
            if deleted:
                messages.success(request, 'لینک فوتر حذف شد.')
            else:
                messages.error(request, 'لینک فوتر یافت نشد.')

        elif action == 'delete_footer_group':
            group_id = request.POST.get('group_id')
            deleted, _ = FooterLinkGroup.objects.filter(id=group_id).delete()
            if deleted:
                messages.success(request, 'گروه فوتر حذف شد.')
            else:
                messages.error(request, 'گروه فوتر یافت نشد.')

        # ─── افزودن/حذف نماد اعتماد ───
        elif action == 'add_trust_badge':
            badge_name = request.POST.get('badge_name', '').strip()
            badge_icon = request.POST.get('badge_icon', 'verified').strip()
            badge_url = request.POST.get('badge_url', '').strip()

            if not badge_name or len(badge_name) < 2:
                messages.error(request, 'نام نماد باید حداقل ۲ کاراکتر باشد.')
            else:
                TrustBadge.objects.create(
                    name=badge_name,
                    icon=badge_icon,
                    link_url=badge_url,
                    order=TrustBadge.objects.count(),
                )
                messages.success(request, f'نماد "{badge_name}" اضافه شد.')

        elif action == 'toggle_trust_badge':
            badge_id = request.POST.get('badge_id')
            try:
                badge = TrustBadge.objects.get(id=badge_id)
                badge.is_active = not badge.is_active
                badge.save(update_fields=['is_active'])
            except TrustBadge.DoesNotExist:
                messages.error(request, 'نماد اعتماد یافت نشد.')

        elif action == 'delete_trust_badge':
            badge_id = request.POST.get('badge_id')
            deleted, _ = TrustBadge.objects.filter(id=badge_id).delete()
            if deleted:
                messages.success(request, 'نماد اعتماد حذف شد.')
            else:
                messages.error(request, 'نماد اعتماد یافت نشد.')

        else:
            messages.error(request, f'عملیات "{action}" ناشناخته است.')

        return redirect(reverse('dashboard:landing_items'))

    # ─── دریافت داده‌ها برای نمایش ───
    nav_items = NavItem.objects.order_by('order')
    footer_groups = FooterLinkGroup.objects.prefetch_related(
        'links'
    ).order_by('order')
    trust_badges = TrustBadge.objects.order_by('order')

    context = {
        'nav_items': nav_items,
        'footer_groups': footer_groups,
        'trust_badges': trust_badges,
    }
    return render(request, 'dashboard/settings/landing_items.html', context)