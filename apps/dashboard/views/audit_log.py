# apps/dashboard/views/audit_log.py
"""
✅ فاز ۱: مشاهده لاگ عملیات — خواندن از دیتابیس
به جای لیست حافظه‌ای که با ریستارت از بین می‌رفت
"""
import logging
from django.core.paginator import Paginator
from django.shortcuts import render
from apps.dashboard.decorators import admin_login_required, role_required
from apps.dashboard.models import AuditLog

logger = logging.getLogger(__name__)


@role_required('super_admin')
@admin_login_required
def audit_log_view(request):
    """نمایش لاگ‌های حسابرسی از دیتابیس"""
    page_number = request.GET.get('page', 1)

    # ─── فیلترها ───
    action_filter = request.GET.get('action', '').strip()
    admin_filter = request.GET.get('admin', '').strip()

    queryset = AuditLog.objects.all().order_by('-created_at')

    if action_filter:
        queryset = queryset.filter(action__icontains=action_filter)

    if admin_filter:
        queryset = queryset.filter(
            admin_phone__icontains=admin_filter,
        )

    # ─── صفحه‌بندی ───
    paginator = Paginator(queryset, 50)
    page_obj = paginator.get_page(page_number)

    # ─── آمار ───
    stats = {
        'total': AuditLog.objects.count(),
        'filtered': queryset.count(),
    }

    context = {
        'page_obj': page_obj,
        'stats': stats,
        'action_filter': action_filter,
        'admin_filter': admin_filter,
        'action_choices': [
            ('business.approved', 'تایید کسب‌وکار'),
            ('business.rejected', 'رد کسب‌وکار'),
            ('business.vip_toggled', 'تغییر وضعیت VIP'),
            ('admin.created', 'ایجاد ادمین'),
            ('admin.deleted', 'حذف ادمین'),
            ('admin.toggled', 'تغییر وضعیت ادمین'),
            ('role.created', 'ایجاد نقش'),
            ('role.edited', 'ویرایش نقش'),
            ('role.deleted', 'حذف نقش'),
            ('settings.system_updated', 'بروزرسانی تنظیمات سیستم'),
            ('settings.sms_template_edited', 'ویرایش قالب پیامک'),
            ('settings.landing_updated', 'بروزرسانی لندینگ'),
            ('financial.settlement_approved', 'تایید تسویه'),
            ('financial.settlement_rejected', 'رد تسویه'),
            ('auth.login', 'ورود به داشبورد'),
            ('auth.logout', 'خروج از داشبورد'),
        ],
    }
    return render(
        request,
        'dashboard/audit_log.html',
        context,
    )