"""
داشبورد اصلی — صفحه خوش‌آمدگویی با آمار واقعی
"""
import logging
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Sum, Q, Avg, F
from django.db.models.functions import TruncDate
from datetime import timedelta

from apps.dashboard.decorators import admin_login_required

logger = logging.getLogger(__name__)


@admin_login_required
def home_view(request):
    """صفحه اصلی داشبورد با آمار"""
    role = request.session.get('dashboard_role', 'super_admin')
    phone = request.session.get('dashboard_admin_phone', '')

    # ═══════════════════════════════════════════
    #   آمار کلی
    # ═══════════════════════════════════════════
    from apps.accounts.models import User
    from apps.businesses.models import Business
    from apps.appointments.models import Appointment
    from apps.payments.models import Transaction, Settlement
    from apps.reviews.models import Review
    from apps.support.models import SupportTicket
    from apps.landing.models import ContactMessage
    from apps.explore.models import ExplorePost
    from apps.portfolios.models import Portfolio

    # ─── کاربران ───
    users_stats = User.objects.aggregate(
        total=Count('id'),
        verified=Count('id', filter=Q(is_verified=True)),
        active=Count('id', filter=Q(is_active=True)),
        new_today=Count('id', filter=Q(date_joined__date=timezone.now().date())),
    )

    # ─── کسب‌وکارها ───
    businesses_stats = Business.objects.aggregate(
        total=Count('id'),
        approved=Count('id', filter=Q(status='approved')),
        pending=Count('id', filter=Q(status='pending')),
        rejected=Count('id', filter=Q(status='rejected')),
    )

    # ─── نوبت‌ها ───
    appointments_stats = Appointment.objects.aggregate(
        total=Count('id'),
        reserved=Count('id', filter=Q(status='reserved')),
        done=Count('id', filter=Q(status='done')),
        cancelled=Count('id', filter=Q(status__in=['cancelled_by_customer', 'cancelled_by_salon'])),
    )

    # ─── تراکنش‌ها ───
    transactions_stats = Transaction.objects.aggregate(
        total=Count('id'),
        total_amount=Sum('amount'),
        blocked=Count('id', filter=Q(status='blocked')),
        settled=Count('id', filter=Q(status='settled')),
    )

    # ─── نظرات ───
    reviews_stats = Review.objects.aggregate(
        total=Count('id'),
        avg_rating=Avg('rating'),
    )

    # ─── تیکت‌ها ───
    tickets_stats = SupportTicket.objects.aggregate(
        total=Count('id'),
        open=Count('id', filter=Q(status='open')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        resolved=Count('id', filter=Q(status='resolved')),
    )

    # ─── پیام‌های تماس ───
    contact_stats = ContactMessage.objects.aggregate(
        total=Count('id'),
        unread=Count('id', filter=Q(is_read=False)),
    )

    # ─── اکسپلور ───
    explore_stats = ExplorePost.objects.aggregate(
        total=Count('id'),
        pinned=Count('id', filter=Q(is_pinned=True)),
    )

    # ─── نمونه‌کارها ───
    portfolios_stats = Portfolio.objects.aggregate(
        total=Count('id'),
    )

    # ═══════════════════════════════════════════
    #   آمار ۷ روز اخیر (برای نمودار)
    # ═══════════════════════════════════════════
    seven_days_ago = timezone.now() - timedelta(days=7)

    # نوبت‌های ۷ روز اخیر
    appointments_7days = (
        Appointment.objects.filter(created_at__gte=seven_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # تراکنش‌های ۷ روز اخیر
    transactions_7days = (
        Transaction.objects.filter(created_at__gte=seven_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'), total=Sum('amount'))
        .order_by('date')
    )

    # کاربران جدید ۷ روز اخیر
    users_7days = (
        User.objects.filter(date_joined__gte=seven_days_ago)
        .annotate(date=TruncDate('date_joined'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # ═══════════════════════════════════════════
    #   لیست‌های اخیر
    # ═══════════════════════════════════════════
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_businesses = Business.objects.order_by('-created_at')[:5]
    recent_appointments = Appointment.objects.select_related(
        'customer', 'business', 'service'
    ).order_by('-created_at')[:5]
    recent_transactions = Transaction.objects.select_related(
        'customer', 'business'
    ).order_by('-created_at')[:5]
    pending_businesses = Business.objects.filter(
        status='pending'
    ).order_by('-created_at')[:5]

    # ═══════════════════════════════════════════
    #   Context
    # ═══════════════════════════════════════════
    context = {
        'role': role,
        'phone': phone,
        'current_time': timezone.now(),
        # آمار
        'users_stats': users_stats,
        'businesses_stats': businesses_stats,
        'appointments_stats': appointments_stats,
        'transactions_stats': transactions_stats,
        'reviews_stats': reviews_stats,
        'tickets_stats': tickets_stats,
        'contact_stats': contact_stats,
        'explore_stats': explore_stats,
        'portfolios_stats': portfolios_stats,
        # نمودارها
        'appointments_7days': list(appointments_7days),
        'transactions_7days': list(transactions_7days),
        'users_7days': list(users_7days),
        # لیست‌ها
        'recent_users': recent_users,
        'recent_businesses': recent_businesses,
        'recent_appointments': recent_appointments,
        'recent_transactions': recent_transactions,
        'pending_businesses': pending_businesses,
    }

    return render(request, 'dashboard/home/index.html', context)