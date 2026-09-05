# apps/dashboard/views/businesses.py
"""
مدیریت کسب‌وکارها — لیست، فیلتر، جزئیات، تایید/رد
✅ فاز ۵: افزودن Audit Log + بهینه‌سازی کوئری‌ها
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from apps.businesses.models import Business
from apps.dashboard.decorators import admin_login_required, role_required
from apps.dashboard.services.audit_service import DashboardAuditService
from apps.dashboard.services.cache_service import DashboardCacheService

logger = logging.getLogger(__name__)


@admin_login_required
def businesses_list_view(request):
    """لیست کسب‌وکارها با جستجو و فیلتر"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page_number = request.GET.get('page', 1)

    queryset = Business.objects.filter(is_active=True).select_related(
        'owner', 'category', 'city', 'province'
    ).annotate(
        services_count=Count('services', filter=Q(services__is_active=True)),
        appointments_count=Count('appointments', filter=Q(appointments__is_active=True)),
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(owner__phone__icontains=search) |
            Q(owner__first_name__icontains=search) |
            Q(city__name__icontains=search)
        )

    if status_filter == 'pending':
        queryset = queryset.filter(status=Business.Status.PENDING)
    elif status_filter == 'approved':
        queryset = queryset.filter(status=Business.Status.APPROVED)
    elif status_filter == 'rejected':
        queryset = queryset.filter(status=Business.Status.REJECTED)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    stats = {
        'total': Business.objects.count(),
        'pending': Business.objects.filter(status=Business.Status.PENDING).count(),
        'approved': Business.objects.filter(status=Business.Status.APPROVED).count(),
        'rejected': Business.objects.filter(status=Business.Status.REJECTED).count(),
    }

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'stats': stats,
    }
    return render(request, 'dashboard/businesses/list.html', context)


@admin_login_required
def business_detail_view(request, business_id):
    """جزئیات کسب‌وکار"""
    business = get_object_or_404(
        Business.objects.select_related(
            'owner', 'category', 'city', 'province'
        ).prefetch_related('services', 'gallery', 'reviews'),
        id=business_id,
    )

    business_stats = {
        'services_count': business.services.filter(is_active=True).count(),
        'appointments_count': business.appointments.count(),
        'reviews_count': business.reviews.count(),
        'avg_rating': business.rating,
        'transactions_count': business.transactions.count(),
        'posts_count': business.posts.count(),
    }

    services = business.services.all()[:10]
    recent_reviews = business.reviews.select_related(
        'customer'
    ).order_by('-created_at')[:5]

    context = {
        'business': business,
        'business_stats': business_stats,
        'services': services,
        'recent_reviews': recent_reviews,
    }
    return render(request, 'dashboard/businesses/detail.html', context)


# ✅ فاز ۳ + ۵: فقط ادمین اپلیکیشن و سوپر ادمین + Audit Log
@role_required('app_admin', 'super_admin')
@admin_login_required
def business_approve_view(request, business_id):
    """تایید کسب‌وکار"""
    business = get_object_or_404(Business, id=business_id)

    if request.method == 'POST':
        business.status = Business.Status.APPROVED
        business.rejection_reason = ''
        business.save(update_fields=['status', 'rejection_reason'])

        # ✅ فاز ۵: بی‌اعتبار کردن کش آمار داشبورد
        DashboardCacheService.invalidate_dashboard_stats()

        # ✅ فاز ۵: ثبت در Audit Log
        DashboardAuditService.log_business_approved(request, business)

        messages.success(request, f'کسب‌وکار "{business.name}" تایید شد.')

        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_business_approved(business)
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")

    return redirect(reverse('dashboard:business_detail', kwargs={'business_id': business_id}))


# ✅ فاز ۳ + ۵: فقط ادمین اپلیکیشن و سوپر ادمین + Audit Log
@role_required('app_admin', 'super_admin')
@admin_login_required
def business_reject_view(request, business_id):
    """رد کسب‌وکار"""
    business = get_object_or_404(Business, id=business_id)

    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        if not reason:
            messages.error(request, 'دلیل رد کسب‌وکار الزامی است.')
            return redirect(reverse('dashboard:business_detail', kwargs={'business_id': business_id}))

        business.status = Business.Status.REJECTED
        business.rejection_reason = reason
        business.save(update_fields=['status', 'rejection_reason'])

        # ✅ فاز ۵: بی‌اعتبار کردن کش آمار داشبورد
        DashboardCacheService.invalidate_dashboard_stats()

        # ✅ فاز ۵: ثبت در Audit Log
        DashboardAuditService.log_business_rejected(request, business, reason)

        messages.warning(request, f'کسب‌وکار "{business.name}" رد شد.')

        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_business_rejected(business)
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {e}")

    return redirect(reverse('dashboard:business_detail', kwargs={'business_id': business_id}))


# ✅ فاز ۳ + ۵: فقط ادمین اپلیکیشن و سوپر ادمین + Audit Log
@role_required('app_admin', 'super_admin')
@admin_login_required
def business_toggle_vip_view(request, business_id):
    """فعال/غیرفعال کردن VIP"""
    business = get_object_or_404(Business, id=business_id)

    if request.method == 'POST':
        business.is_vip = not business.is_vip
        business.save(update_fields=['is_vip'])

        # ✅ فاز ۵: بی‌اعتبار کردن کش آمار داشبورد
        DashboardCacheService.invalidate_dashboard_stats()

        # ✅ فاز ۵: ثبت در Audit Log
        DashboardAuditService.log_business_vip_toggled(
            request, business, business.is_vip
        )

        status_text = 'VIP شد' if business.is_vip else 'از VIP خارج شد'
        messages.success(request, f'کسب‌وکار "{business.name}" {status_text}.')

        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                user=business.owner,
                type='system',
                title=f'کسب‌وکار شما {status_text}',
                body=(
                    f'کسب‌وکار "{business.name}" '
                    f'{"به لیست کسب‌وکارهای ویژه اضافه شد."
                     if business.is_vip else
                     "از لیست کسب‌وکارهای ویژه خارج شد."}'
                ),
                data={'business_id': business.id},
                channels=['in_app'],
            )
        except Exception as e:
            logger.error(f"Failed to send VIP notification: {e}")

    return redirect(reverse('dashboard:business_detail', kwargs={'business_id': business_id}))