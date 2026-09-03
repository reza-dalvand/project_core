"""
مدیریت مالی — تراکنش‌ها، تسویه‌ها، آمار
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Sum, Count, Avg, F
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from apps.payments.models import Transaction, Settlement
from apps.dashboard.decorators import admin_login_required

logger = logging.getLogger(__name__)


@admin_login_required
def financial_index_view(request):
    """داشبورد مالی اصلی با آمار"""
    # ─── آمار کلی تراکنش‌ها ───
    tx_stats = Transaction.objects.aggregate(
        total_count=Count('id'),
        total_amount=Sum('amount'),
        total_fee=Sum('app_fee'),
        blocked_count=Count('id', filter=Q(status=Transaction.Status.BLOCKED)),
        blocked_amount=Sum('amount', filter=Q(status=Transaction.Status.BLOCKED)),
        settling_count=Count('id', filter=Q(status=Transaction.Status.SETTLING)),
        settling_amount=Sum('amount', filter=Q(status=Transaction.Status.SETTLING)),
        settled_count=Count('id', filter=Q(status=Transaction.Status.SETTLED)),
        settled_amount=Sum('amount', filter=Q(status=Transaction.Status.SETTLED)),
        refunded_count=Count('id', filter=Q(status=Transaction.Status.REFUNDED)),
        refunded_amount=Sum('amount', filter=Q(status=Transaction.Status.REFUNDED)),
        failed_count=Count('id', filter=Q(status=Transaction.Status.FAILED)),
    )

    # ─── آمار تسویه‌ها ───
    settlement_stats = Settlement.objects.aggregate(
        total_count=Count('id'),
        total_amount=Sum('amount'),
        pending_count=Count('id', filter=Q(status=Settlement.Status.PENDING)),
        pending_amount=Sum('amount', filter=Q(status=Settlement.Status.PENDING)),
        processing_count=Count('id', filter=Q(status=Settlement.Status.PROCESSING)),
        completed_count=Count('id', filter=Q(status=Settlement.Status.COMPLETED)),
        completed_amount=Sum('amount', filter=Q(status=Settlement.Status.COMPLETED)),
        failed_count=Count('id', filter=Q(status=Settlement.Status.FAILED)),
    )

    # ─── آمار ۳۰ روز اخیر ───
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_tx = (
        Transaction.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'), total=Sum('amount'))
        .order_by('date')
    )

    # ─── تراکنش‌های اخیر ───
    recent_transactions = Transaction.objects.select_related(
        'customer', 'business', 'appointment'
    ).order_by('-created_at')[:10]

    # ─── تسویه‌های در انتظار ───
    pending_settlements = Settlement.objects.select_related(
        'business'
    ).filter(
        status=Settlement.Status.PENDING
    ).order_by('-created_at')[:5]

    context = {
        'tx_stats': tx_stats,
        'settlement_stats': settlement_stats,
        'monthly_tx': list(monthly_tx),
        'recent_transactions': recent_transactions,
        'pending_settlements': pending_settlements,
    }
    return render(request, 'dashboard/financial/index.html', context)


@admin_login_required
def transactions_list_view(request):
    """لیست تراکنش‌ها با فیلتر و جستجو"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    page_number = request.GET.get('page', 1)

    queryset = Transaction.objects.select_related(
        'customer', 'business', 'appointment'
    ).order_by('-created_at')

    # جستجو
    if search:
        queryset = queryset.filter(
            Q(tracking_code__icontains=search) |
            Q(ref_number__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(business__name__icontains=search) |
            Q(gateway_transaction_id__icontains=search)
        )

    # فیلتر وضعیت
    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    # فیلتر نوع
    if type_filter != 'all':
        queryset = queryset.filter(type=type_filter)

    # صفحه‌بندی
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    # آمار سریع
    stats = {
        'total': Transaction.objects.count(),
        'blocked': Transaction.objects.filter(status=Transaction.Status.BLOCKED).count(),
        'settling': Transaction.objects.filter(status=Transaction.Status.SETTLING).count(),
        'settled': Transaction.objects.filter(status=Transaction.Status.SETTLED).count(),
        'refunded': Transaction.objects.filter(status=Transaction.Status.REFUNDED).count(),
        'failed': Transaction.objects.filter(status=Transaction.Status.FAILED).count(),
    }

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'stats': stats,
        'status_choices': Transaction.Status.choices,
        'type_choices': Transaction.Type.choices,
    }
    return render(request, 'dashboard/financial/transactions_list.html', context)


@admin_login_required
def transaction_detail_view(request, transaction_id):
    """جزئیات تراکنش"""
    transaction = get_object_or_404(
        Transaction.objects.select_related(
            'customer', 'business', 'appointment', 'appointment__service'
        ),
        id=transaction_id,
    )

    context = {
        'transaction': transaction,
    }
    return render(request, 'dashboard/financial/transaction_detail.html', context)


@admin_login_required
def settlements_list_view(request):
    """لیست تسویه‌ها با فیلتر"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page_number = request.GET.get('page', 1)

    queryset = Settlement.objects.select_related(
        'business', 'business__owner'
    ).order_by('-created_at')

    # جستجو
    if search:
        queryset = queryset.filter(
            Q(business__name__icontains=search) |
            Q(business__owner__phone__icontains=search) |
            Q(bank_sheba__icontains=search) |
            Q(bank_name__icontains=search)
        )

    # فیلتر وضعیت
    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    # صفحه‌بندی
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    # آمار سریع
    stats = {
        'total': Settlement.objects.count(),
        'pending': Settlement.objects.filter(status=Settlement.Status.PENDING).count(),
        'processing': Settlement.objects.filter(status=Settlement.Status.PROCESSING).count(),
        'completed': Settlement.objects.filter(status=Settlement.Status.COMPLETED).count(),
        'failed': Settlement.objects.filter(status=Settlement.Status.FAILED).count(),
    }

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'stats': stats,
        'status_choices': Settlement.Status.choices,
    }
    return render(request, 'dashboard/financial/settlements_list.html', context)


@admin_login_required
def settlement_approve_view(request, settlement_id):
    """تایید و پردازش تسویه"""
    settlement = get_object_or_404(Settlement, id=settlement_id)

    if request.method == 'POST':
        if settlement.status != Settlement.Status.PENDING:
            messages.error(request, 'این تسویه قابل پردازش نیست.')
            return redirect(reverse('dashboard:settlements_list'))

        try:
            from apps.payments.services.payment_service import PaymentService
            PaymentService.process_settlement(settlement)

            messages.success(
                request,
                f'تسویه کسب‌وکار "{settlement.business.name}" '
                f'به مبلغ {settlement.amount:,} تومان پردازش شد.'
            )
            logger.info(f"Settlement approved: {settlement.id}")

        except Exception as e:
            messages.error(request, f'خطا در پردازش تسویه: {str(e)}')
            logger.error(f"Settlement approval error: {e}")

    return redirect(reverse('dashboard:settlements_list'))


@admin_login_required
def settlement_reject_view(request, settlement_id):
    """رد تسویه"""
    settlement = get_object_or_404(Settlement, id=settlement_id)

    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        if not reason:
            messages.error(request, 'دلیل رد تسویه الزامی است.')
            return redirect(reverse('dashboard:settlements_list'))

        if settlement.status != Settlement.Status.PENDING:
            messages.error(request, 'این تسویه قابل رد نیست.')
            return redirect(reverse('dashboard:settlements_list'))

        settlement.status = Settlement.Status.FAILED
        settlement.save(update_fields=['status'])

        messages.warning(
            request,
            f'تسویه کسب‌وکار "{settlement.business.name}" رد شد.'
        )
        logger.info(f"Settlement rejected: {settlement.id} (reason: {reason})")

    return redirect(reverse('dashboard:settlements_list'))