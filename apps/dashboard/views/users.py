"""
مدیریت کاربران — لیست، جستجو، فیلتر، جزئیات، فعال/غیرفعال
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.core.paginator import Paginator

from apps.dashboard.decorators import admin_login_required

logger = logging.getLogger(__name__)
User = get_user_model()


@admin_login_required
def users_list_view(request):
    """لیست کاربران با جستجو و فیلتر"""
    # ─── فیلترها ───
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page_number = request.GET.get('page', 1)

    queryset = User.objects.annotate(
        businesses_count=Count('businesses'),
        appointments_count=Count('appointments'),
    ).order_by('-date_joined')

    # جستجو
    if search:
        queryset = queryset.filter(
            Q(phone__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(national_id__icontains=search)
        )

    # فیلتر وضعیت
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True, is_verified=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)
    elif status_filter == 'unverified':
        queryset = queryset.filter(is_verified=False)
    elif status_filter == 'staff':
        queryset = queryset.filter(is_staff=True)
    elif status_filter == 'business_owner':
        queryset = queryset.filter(businesses__isnull=False).distinct()

    # صفحه‌بندی
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    # آمار سریع
    stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True, is_verified=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
        'unverified': User.objects.filter(is_verified=False).count(),
        'staff': User.objects.filter(is_staff=True).count(),
    }

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'stats': stats,
    }
    return render(request, 'dashboard/users/list.html', context)


@admin_login_required
def user_detail_view(request, user_id):
    """جزئیات کاربر"""
    user = get_object_or_404(
        User.objects.prefetch_related('businesses', 'appointments'),
        id=user_id,
    )

    # آمار کاربر
    user_stats = {
        'businesses_count': user.businesses.count(),
        'appointments_count': user.appointments.count(),
        'transactions_count': user.transactions.count(),
        'reviews_count': user.reviews.count(),
        'favorites_count': user.favorite_businesses.count(),
    }

    # کسب‌وکارهای کاربر
    user_businesses = user.businesses.all()

    # نوبت‌های اخیر
    recent_appointments = user.appointments.select_related(
        'business', 'service'
    ).order_by('-created_at')[:5]

    context = {
        'user_obj': user,
        'user_stats': user_stats,
        'user_businesses': user_businesses,
        'recent_appointments': recent_appointments,
    }
    return render(request, 'dashboard/users/detail.html', context)


@admin_login_required
def user_toggle_active_view(request, user_id):
    """فعال/غیرفعال کردن کاربر"""
    user = get_object_or_404(User, id=user_id)

    # جلوگیری از غیرفعال کردن خودتان
    admin_phone = request.session.get('dashboard_admin_phone')
    if user.phone == admin_phone:
        messages.error(request, 'نمی‌توانید حساب خودتان را غیرفعال کنید.')
        return redirect(reverse('dashboard:user_detail', kwargs={'user_id': user_id}))

    # جلوگیری از غیرفعال کردن سوپرادمین
    if user.is_superuser:
        messages.error(request, 'نمی‌توانید حساب سوپرادمین را غیرفعال کنید.')
        return redirect(reverse('dashboard:user_detail', kwargs={'user_id': user_id}))

    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])

        status_text = 'فعال' if user.is_active else 'غیرفعال'
        messages.success(request, f'کاربر {user.phone} {status_text} شد.')
        logger.info(f"Admin toggled user {user.phone} to {status_text}")

    return redirect(reverse('dashboard:user_detail', kwargs={'user_id': user_id}))