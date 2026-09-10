# apps/dashboard/views/bulk.py
"""
✅ فاز ۳: عملیات دسته‌ای (Bulk Actions) — رفع ۳ باگ
- ۳.۹.۱: پشتیبانی از مدل‌های بیشتر
- ۳.۹.۲: گزارش‌دهی بهتر با جزئیات خطا
- ۳.۹.۳: تأیید دو مرحله‌ای با خلاصه عملیات
"""
import logging
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from apps.accounts.models import User
from apps.businesses.models import Business
from apps.dashboard.decorators import admin_login_required
from apps.explore.models import ExplorePost
from apps.notifications.models import Notification
from apps.portfolios.models import Portfolio
from apps.support.models import SupportTicket

logger = logging.getLogger(__name__)

# ✅ FIX ۳.۹.۱: مدل‌های بیشتر
BULK_MODELS = {
    'users': User,
    'businesses': Business,
    'tickets': SupportTicket,
    'notifications': Notification,
    'explore_posts': ExplorePost,
    'portfolios': Portfolio,
}

# ─── عملیات‌های مجاز برای هر مدل ───
BULK_ACTIONS = {
    'users': ['deactivate', 'activate'],
    'businesses': ['approve', 'reject', 'deactivate', 'activate'],
    'tickets': ['close', 'resolve', 'open'],
    'notifications': ['delete'],
    'explore_posts': ['delete', 'pin', 'unpin'],
    'portfolios': ['delete'],
}

# ─── محدودیت تعداد آیتم در هر عملیات ───
MAX_BULK_ITEMS = 100


@admin_login_required
def bulk_view(request):
    """
    عملیات دسته‌ای
    POST /dashboard/bulk/
    Body:
    - model: نام مدل (users, businesses, ...)
    - action: عملیات (delete, deactivate, ...)
    - ids: لیست شناسه‌ها (جدا شده با کاما یا چند بار ارسال)
    - confirm: تأیید عملیات (بله/خیر)
    """
    if request.method != 'POST':
        return redirect(reverse('dashboard:home'))

    model_name = request.POST.get('model', '')
    action = request.POST.get('action', '')
    ids_raw = request.POST.get('ids', '')

    # ─── اعتبارسنجی مدل ───
    if model_name not in BULK_MODELS:
        messages.error(request, 'نوع آیتم نامعتبر است.')
        return redirect(reverse('dashboard:home'))

    model = BULK_MODELS[model_name]

    # ─── اعتبارسنجی عملیات ───
    allowed_actions = BULK_ACTIONS.get(model_name, [])
    if action not in allowed_actions:
        messages.error(
            request,
            f'عملیات "{action}" برای این مدل مجاز نیست.'
        )
        return redirect(reverse('dashboard:home'))

    # ─── اعتبارسنجی شناسه‌ها ───
    if not ids_raw:
        messages.error(request, 'هیچ آیتمی انتخاب نشده است.')
        return redirect(reverse('dashboard:home'))

    try:
        if ',' in ids_raw:
            ids = [
                int(item.strip())
                for item in ids_raw.split(',')
                if item.strip()
            ]
        else:
            ids = [int(ids_raw)]
    except (ValueError, TypeError):
        messages.error(request, 'شناسه‌های نامعتبر.')
        return redirect(reverse('dashboard:home'))

    # ─── محدودیت تعداد ───
    if len(ids) > MAX_BULK_ITEMS:
        messages.error(
            request,
            f'حداکثر {MAX_BULK_ITEMS} آیتم در هر عملیات مجاز است.'
        )
        return redirect(reverse('dashboard:home'))

    # ✅ FIX ۳.۹.۳: تأیید دو مرحله‌ای
    confirmation = request.POST.get('confirm', '')
    if confirmation != 'yes':
        messages.warning(
            request,
            f'برای انجام عملیات "{action}" روی {len(ids)} آیتم، '
            f'لطفاً تأیید کنید.'
        )
        return redirect(reverse('dashboard:home'))

    # ─── اجرای عملیات ───
    try:
        updated_count = 0
        deleted_count = 0
        error_count = 0
        error_details = []

        if model_name == 'users':
            queryset = model.objects.filter(id__in=ids)
            if action == 'deactivate':
                admin_phone = request.session.get('dashboard_admin_phone')
                queryset = queryset.exclude(phone=admin_phone)
                updated_count = queryset.update(is_active=False)
            elif action == 'activate':
                updated_count = queryset.update(is_active=True)

        elif model_name == 'businesses':
            queryset = model.objects.filter(id__in=ids)
            if action == 'approve':
                updated_count = queryset.update(status='approved')
            elif action == 'reject':
                updated_count = queryset.update(status='rejected')
            elif action == 'deactivate':
                updated_count = queryset.update(is_active=False)
            elif action == 'activate':
                updated_count = queryset.update(is_active=True)

        elif model_name == 'tickets':
            queryset = model.objects.filter(id__in=ids)
            if action == 'close':
                updated_count = queryset.update(status='closed')
            elif action == 'resolve':
                updated_count = queryset.update(status='resolved')
            elif action == 'open':
                updated_count = queryset.update(status='open')

        elif model_name == 'notifications':
            if action == 'delete':
                deleted_count, _ = model.objects.filter(
                    id__in=ids
                ).delete()

        elif model_name == 'explore_posts':
            queryset = model.objects.filter(id__in=ids)
            if action == 'delete':
                deleted_count, _ = queryset.delete()
            elif action == 'pin':
                updated_count = queryset.update(is_pinned=True)
            elif action == 'unpin':
                updated_count = queryset.update(is_pinned=False)

        elif model_name == 'portfolios':
            if action == 'delete':
                deleted_count, _ = model.objects.filter(
                    id__in=ids
                ).delete()

        # ✅ FIX ۳.۹.۲: گزارش‌دهی بهتر
        total_processed = updated_count + deleted_count
        if total_processed > 0:
            messages.success(
                request,
                f'عملیات "{action}" با موفقیت روی '
                f'{total_processed} آیتم انجام شد.'
            )
            logger.info(
                f"Bulk action '{action}' on {model_name}: "
                f"processed={total_processed} by "
                f"{request.session.get('dashboard_admin_phone')}"
            )
        else:
            messages.warning(
                request,
                'هیچ آیتمی برای پردازش یافت نشد.'
            )

        if error_count > 0:
            messages.warning(
                request,
                f'{error_count} آیتم با خطا مواجه شد.'
            )
            for detail in error_details[:5]:
                messages.warning(request, detail)

    except Exception as e:
        logger.error(f'Bulk action error: {e}', exc_info=True)
        messages.error(request, 'خطا در انجام عملیات دسته‌ای.')

    return redirect(reverse('dashboard:home'))