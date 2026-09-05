# apps/dashboard/views/financial.py
"""
مدیریت مالی — تراکنش‌ها، تسویه‌ها، آمار
✅ فاز ۳: رفع ۶ باگ
- ۳.۳.۱: اعتبارسنجی سقف مبلغ در transaction_create_view
- ۳.۳.۲: جلوگیری از تغییر مبلغ پس از تسویه
- ۳.۳.۳: بررسی موجودی قابل تسویه قبل از ایجاد
- ۳.۳.۴: فرآیند تسویه با وضعیت‌های صحیح
- ۳.۳.۵: فیلتر تاریخ با timezone awareness
- ۳.۳.۶: ارسال اعلان در رد تسویه
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction as db_transaction
from datetime import timedelta, datetime
from apps.payments.models import Transaction, Settlement
from apps.dashboard.decorators import admin_login_required, role_required
from apps.dashboard.services.audit_service import DashboardAuditService
from apps.dashboard.services.cache_service import DashboardCacheService

logger = logging.getLogger(__name__)

# ✅ FIX ۳.۳.۱: سقف مبلغ تراکنش دستی
MAX_MANUAL_TRANSACTION_AMOUNT = 500_000_000  # ۵۰۰ میلیون تومان


# ═══════════════════════════════════════════════
#   داشبورد مالی
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def financial_index_view(request):
    """داشبورد مالی اصلی با آمار"""
    tx_stats = DashboardCacheService.get_dashboard_stats()
    if tx_stats is None:
        tx_stats = Transaction.objects.filter(is_active=True).aggregate(
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
        DashboardCacheService.set_dashboard_stats(tx_stats)

    settlement_stats = Settlement.objects.filter(is_active=True).aggregate(
        total_count=Count('id'),
        total_amount=Sum('amount'),
        pending_count=Count('id', filter=Q(status=Settlement.Status.PENDING)),
        pending_amount=Sum('amount', filter=Q(status=Settlement.Status.PENDING)),
        processing_count=Count('id', filter=Q(status=Settlement.Status.PROCESSING)),
        completed_count=Count('id', filter=Q(status=Settlement.Status.COMPLETED)),
        completed_amount=Sum('amount', filter=Q(status=Settlement.Status.COMPLETED)),
        failed_count=Count('id', filter=Q(status=Settlement.Status.FAILED)),
    )

    # آمار روزانه/هفتگی/ماهانه
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    daily_stats = Transaction.objects.filter(
        created_at__gte=today_start, is_active=True
    ).aggregate(count=Count('id'), amount=Sum('amount'))

    weekly_stats = Transaction.objects.filter(
        created_at__gte=week_start, is_active=True
    ).aggregate(count=Count('id'), amount=Sum('amount'))

    monthly_stats = Transaction.objects.filter(
        created_at__gte=month_start, is_active=True
    ).aggregate(count=Count('id'), amount=Sum('amount'))

    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_tx = (
        Transaction.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'), total=Sum('amount'))
        .order_by('date')
    )

    recent_transactions = Transaction.objects.select_related(
        'customer', 'business', 'appointment'
    ).order_by('-created_at')[:10]

    pending_settlements = Settlement.objects.select_related(
        'business'
    ).filter(
        status=Settlement.Status.PENDING
    ).order_by('-created_at')[:5]

    context = {
        'tx_stats': tx_stats,
        'settlement_stats': settlement_stats,
        'daily_stats': daily_stats,
        'weekly_stats': weekly_stats,
        'monthly_stats': monthly_stats,
        'monthly_tx': list(monthly_tx),
        'recent_transactions': recent_transactions,
        'pending_settlements': pending_settlements,
    }
    return render(request, 'dashboard/financial/index.html', context)


# ═══════════════════════════════════════════════
#   تراکنش‌ها
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def transactions_list_view(request):
    """لیست تراکنش‌ها با فیلتر و جستجو"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    page_number = request.GET.get('page', 1)

    queryset = Transaction.objects.select_related(
        'customer', 'business', 'appointment'
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(tracking_code__icontains=search) |
            Q(ref_number__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(business__name__icontains=search) |
            Q(gateway_transaction_id__icontains=search)
        )

    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    if type_filter != 'all':
        queryset = queryset.filter(type=type_filter)

    # ✅ FIX ۳.۳.۵: فیلتر تاریخ با timezone awareness
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            dt_from = timezone.make_aware(dt_from)
            queryset = queryset.filter(created_at__gte=dt_from)
        except (ValueError, TypeError):
            pass

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, '%Y-%m-%d')
            dt_to = timezone.make_aware(
                dt_to.replace(hour=23, minute=59, second=59)
            )
            queryset = queryset.filter(created_at__lte=dt_to)
        except (ValueError, TypeError):
            pass

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

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
        'date_from': date_from,
        'date_to': date_to,
        'stats': stats,
        'status_choices': Transaction.Status.choices,
        'type_choices': Transaction.Type.choices,
    }
    return render(request, 'dashboard/financial/transactions_list.html', context)


# ═══════════════════════════════════════════════
#   ایجاد تراکنش دستی
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def transaction_create_view(request):
    """ایجاد تراکنش دستی توسط ادمین"""
    from django.contrib.auth import get_user_model
    from apps.businesses.models import Business
    User = get_user_model()

    if request.method == 'POST':
        customer_phone = request.POST.get('customer_phone', '').strip()
        business_id = request.POST.get('business')
        tx_type = request.POST.get('type', '')
        amount_str = request.POST.get('amount', '').strip()
        gateway = request.POST.get('gateway', 'manual')
        gateway_tx_id = request.POST.get('gateway_transaction_id', '').strip()
        card_number = request.POST.get('card_number', '').strip()
        card_bank = request.POST.get('card_bank', '').strip()

        # اعتبارسنجی
        if not customer_phone:
            messages.error(request, 'شماره تلفن مشتری الزامی است.')
            return redirect(reverse('dashboard:transaction_create'))

        try:
            customer = User.objects.get(phone=customer_phone)
        except User.DoesNotExist:
            messages.error(request, 'مشتری با این شماره یافت نشد.')
            return redirect(reverse('dashboard:transaction_create'))

        if not business_id:
            messages.error(request, 'انتخاب کسب‌وکار الزامی است.')
            return redirect(reverse('dashboard:transaction_create'))

        try:
            business = Business.objects.get(id=business_id)
        except Business.DoesNotExist:
            messages.error(request, 'کسب‌وکار یافت نشد.')
            return redirect(reverse('dashboard:transaction_create'))

        if tx_type not in dict(Transaction.Type.choices):
            messages.error(request, 'نوع تراکنش نامعتبر است.')
            return redirect(reverse('dashboard:transaction_create'))

        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'مبلغ باید عدد مثبت باشد.')
            return redirect(reverse('dashboard:transaction_create'))

        # ✅ FIX ۳.۳.۱: اعتبارسنجی سقف مبلغ
        if amount > MAX_MANUAL_TRANSACTION_AMOUNT:
            messages.error(
                request,
                f'مبلغ تراکنش نمی‌تواند بیشتر از '
                f'{MAX_MANUAL_TRANSACTION_AMOUNT:,} تومان باشد.'
            )
            return redirect(reverse('dashboard:transaction_create'))

        # محاسبه کارمزد
        from apps.core.utils import calculate_app_fee
        app_fee = calculate_app_fee(amount)

        # ایجاد تراکنش
        try:
            tx = Transaction.objects.create(
                business=business,
                customer=customer,
                type=tx_type,
                amount=amount,
                app_fee=app_fee,
                status=Transaction.Status.BLOCKED,
                gateway=gateway,
                gateway_transaction_id=gateway_tx_id,
                card_number=card_number,
                card_bank=card_bank,
            )
            DashboardCacheService.invalidate_dashboard_stats()
            logger.info(
                f"Admin created transaction {tx.tracking_code} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(
                request,
                f'تراکنش {tx.tracking_code} با موفقیت ایجاد شد.'
            )
            return redirect(
                reverse('dashboard:transaction_detail',
                        kwargs={'transaction_id': tx.id})
            )
        except Exception as e:
            logger.error(f"Transaction create error: {e}", exc_info=True)
            messages.error(request, 'خطا در ایجاد تراکنش.')

    # نمایش فرم
    businesses = Business.objects.filter(is_active=True).order_by('name')
    context = {
        'businesses': businesses,
        'type_choices': Transaction.Type.choices,
    }
    return render(request, 'dashboard/financial/transaction_create.html', context)


# ═══════════════════════════════════════════════
#   ویرایش تراکنش
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def transaction_edit_view(request, transaction_id):
    """ویرایش تراکنش"""
    tx = get_object_or_404(Transaction, id=transaction_id)

    if request.method == 'POST':
        new_status = request.POST.get('status', tx.status)
        amount_str = request.POST.get('amount', str(tx.amount)).strip()
        gateway_tx_id = request.POST.get('gateway_transaction_id', tx.gateway_transaction_id).strip()
        card_number = request.POST.get('card_number', tx.card_number).strip()
        card_bank = request.POST.get('card_bank', tx.card_bank).strip()
        refund_reason = request.POST.get('refund_reason', tx.refund_reason).strip()

        # اعتبارسنجی وضعیت
        if new_status not in dict(Transaction.Status.choices):
            messages.error(request, 'وضعیت نامعتبر است.')
            return redirect(
                reverse('dashboard:transaction_edit',
                        kwargs={'transaction_id': transaction_id})
            )

        # ✅ FIX ۳.۳.۲: جلوگیری از تغییر مبلغ پس از تسویه
        if tx.status in [Transaction.Status.SETTLED, Transaction.Status.REFUNDED]:
            messages.error(
                request,
                'مبلغ تراکنش‌های تسویه شده یا مسترد شده قابل تغییر نیست.'
            )
            return redirect(
                reverse('dashboard:transaction_edit',
                        kwargs={'transaction_id': transaction_id})
            )

        # اعتبارسنجی مبلغ
        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'مبلغ باید عدد مثبت باشد.')
            return redirect(
                reverse('dashboard:transaction_edit',
                        kwargs={'transaction_id': transaction_id})
            )

        # ✅ FIX ۳.۳.۱: اعتبارسنجی سقف مبلغ
        if amount > MAX_MANUAL_TRANSACTION_AMOUNT:
            messages.error(
                request,
                f'مبلغ تراکنش نمی‌تواند بیشتر از '
                f'{MAX_MANUAL_TRANSACTION_AMOUNT:,} تومان باشد.'
            )
            return redirect(
                reverse('dashboard:transaction_edit',
                        kwargs={'transaction_id': transaction_id})
            )

        # بروزرسانی
        try:
            tx.status = new_status
            tx.amount = amount
            tx.gateway_transaction_id = gateway_tx_id
            tx.card_number = card_number
            tx.card_bank = card_bank
            tx.refund_reason = refund_reason

            if new_status == Transaction.Status.SETTLED and not tx.settled_at:
                tx.settled_at = timezone.now()

            tx.save()
            DashboardCacheService.invalidate_dashboard_stats()
            logger.info(
                f"Admin edited transaction {tx.tracking_code} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(request, 'تراکنش با موفقیت بروزرسانی شد.')
            return redirect(
                reverse('dashboard:transaction_detail',
                        kwargs={'transaction_id': transaction_id})
            )
        except Exception as e:
            logger.error(f"Transaction edit error: {e}", exc_info=True)
            messages.error(request, 'خطا در بروزرسانی تراکنش.')

    context = {
        'transaction': tx,
        'status_choices': Transaction.Status.choices,
    }
    return render(request, 'dashboard/financial/transaction_edit.html', context)


@role_required('financial_admin', 'super_admin')
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


# ═══════════════════════════════════════════════
#   تسویه‌ها
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def settlements_list_view(request):
    """لیست تسویه‌ها با فیلتر"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page_number = request.GET.get('page', 1)

    queryset = Settlement.objects.select_related(
        'business', 'business__owner'
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(business__name__icontains=search) |
            Q(business__owner__phone__icontains=search) |
            Q(bank_sheba__icontains=search) |
            Q(bank_name__icontains=search)
        )

    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

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


# ═══════════════════════════════════════════════
#   ایجاد تسویه دستی
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def settlement_create_view(request):
    """ایجاد تسویه دستی توسط ادمین"""
    from apps.businesses.models import Business

    if request.method == 'POST':
        business_id = request.POST.get('business')
        amount_str = request.POST.get('amount', '').strip()
        bank_sheba = request.POST.get('bank_sheba', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()

        # اعتبارسنجی
        if not business_id:
            messages.error(request, 'انتخاب کسب‌وکار الزامی است.')
            return redirect(reverse('dashboard:settlement_create'))

        try:
            business = Business.objects.get(id=business_id)
        except Business.DoesNotExist:
            messages.error(request, 'کسب‌وکار یافت نشد.')
            return redirect(reverse('dashboard:settlement_create'))

        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'مبلغ باید عدد مثبت باشد.')
            return redirect(reverse('dashboard:settlement_create'))

        if not bank_sheba or len(bank_sheba) != 26:
            messages.error(request, 'شماره شبا باید ۲۶ کاراکتر باشد (IR + ۲۴ رقم).')
            return redirect(reverse('dashboard:settlement_create'))

        if not bank_name:
            messages.error(request, 'نام بانک الزامی است.')
            return redirect(reverse('dashboard:settlement_create'))

        # ✅ FIX ۳.۳.۳: بررسی موجودی قابل تسویه
        from apps.payments.services.payment_service import PaymentService
        balances = PaymentService.get_business_pending_balance(business)
        available_balance = balances.get('settling', 0)

        if amount > available_balance:
            messages.error(
                request,
                f'مبلغ تسویه ({amount:,} تومان) بیشتر از '
                f'موجودی قابل تسویه ({available_balance:,} تومان) است.'
            )
            return redirect(reverse('dashboard:settlement_create'))

        # ایجاد تسویه
        try:
            settlement = Settlement.objects.create(
                business=business,
                amount=amount,
                bank_sheba=bank_sheba,
                bank_name=bank_name,
            )
            DashboardCacheService.invalidate_dashboard_stats()
            logger.info(
                f"Admin created settlement for {business.name} "
                f"amount={amount} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(
                request,
                f'تسویه برای "{business.name}" به مبلغ {amount:,} تومان ایجاد شد.'
            )
            return redirect(reverse('dashboard:settlements_list'))
        except Exception as e:
            logger.error(f"Settlement create error: {e}", exc_info=True)
            messages.error(request, 'خطا در ایجاد تسویه.')

    # نمایش فرم
    businesses = Business.objects.filter(
        is_active=True, status='approved'
    ).order_by('name')
    context = {
        'businesses': businesses,
    }
    return render(request, 'dashboard/financial/settlement_create.html', context)


# ═══════════════════════════════════════════════
#   ویرایش تسویه
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def settlement_edit_view(request, settlement_id):
    """ویرایش تسویه — فقط تسویه‌های PENDING"""
    settlement = get_object_or_404(Settlement, id=settlement_id)

    if settlement.status != Settlement.Status.PENDING:
        messages.error(request, 'فقط تسویه‌های در انتظار قابل ویرایش هستند.')
        return redirect(reverse('dashboard:settlements_list'))

    if request.method == 'POST':
        amount_str = request.POST.get('amount', str(settlement.amount)).strip()
        bank_sheba = request.POST.get('bank_sheba', settlement.bank_sheba).strip()
        bank_name = request.POST.get('bank_name', settlement.bank_name).strip()

        # اعتبارسنجی
        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'مبلغ باید عدد مثبت باشد.')
            return redirect(
                reverse('dashboard:settlement_edit',
                        kwargs={'settlement_id': settlement_id})
            )

        if not bank_sheba or len(bank_sheba) != 26:
            messages.error(request, 'شماره شبا باید ۲۶ کاراکتر باشد.')
            return redirect(
                reverse('dashboard:settlement_edit',
                        kwargs={'settlement_id': settlement_id})
            )

        # بروزرسانی
        try:
            settlement.amount = amount
            settlement.bank_sheba = bank_sheba
            settlement.bank_name = bank_name
            settlement.save(update_fields=['amount', 'bank_sheba', 'bank_name'])
            DashboardCacheService.invalidate_dashboard_stats()
            logger.info(
                f"Admin edited settlement {settlement_id} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(request, 'تسویه با موفقیت بروزرسانی شد.')
            return redirect(reverse('dashboard:settlements_list'))
        except Exception as e:
            logger.error(f"Settlement edit error: {e}", exc_info=True)
            messages.error(request, 'خطا در بروزرسانی تسویه.')

    context = {
        'settlement': settlement,
    }
    return render(request, 'dashboard/financial/settlement_edit.html', context)


# ═══════════════════════════════════════════════
#   حذف تسویه
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def settlement_delete_view(request, settlement_id):
    """حذف تسویه — فقط تسویه‌های ناموفق"""
    settlement = get_object_or_404(Settlement, id=settlement_id)

    if settlement.status not in [Settlement.Status.FAILED, Settlement.Status.PENDING]:
        messages.error(
            request,
            'فقط تسویه‌های ناموفق یا در انتظار قابل حذف هستند.'
        )
        return redirect(reverse('dashboard:settlements_list'))

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:settlements_list'))

        try:
            business_name = settlement.business.name
            settlement.is_active = False
            settlement.save(update_fields=['is_active'])
            DashboardCacheService.invalidate_dashboard_stats()
            logger.info(
                f"Admin soft-deleted settlement {settlement_id} "
                f"for {business_name} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(request, f'تسویه "{business_name}" حذف شد.')
            return redirect(reverse('dashboard:settlements_list'))
        except Exception as e:
            logger.error(f"Settlement delete error: {e}", exc_info=True)
            messages.error(request, 'خطا در حذف تسویه.')

    return redirect(reverse('dashboard:settlements_list'))


# ═══════════════════════════════════════════════
#   تایید تسویه
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
@admin_login_required
def settlement_approve_view(request, settlement_id):
    """تایید و پردازش تسویه"""
    settlement = get_object_or_404(Settlement, id=settlement_id)

    if request.method == 'POST':
        if settlement.status != Settlement.Status.PENDING:
            messages.error(request, 'این تسویه قابل پردازش نیست.')
            return redirect(reverse('dashboard:settlements_list'))

        try:
            # ✅ FIX ۳.۳.۴: فرآیند تسویه با وضعیت‌های صحیح
            with db_transaction.atomic():
                from apps.payments.services.payment_service import PaymentService
                PaymentService.process_settlement(settlement)

            DashboardCacheService.invalidate_dashboard_stats()
            DashboardAuditService.log_settlement_approved(request, settlement)

            messages.success(
                request,
                f'تسویه کسب‌وکار "{settlement.business.name}" '
                f'به مبلغ {settlement.amount:,} تومان پردازش شد.'
            )
        except Exception as e:
            messages.error(request, f'خطا در پردازش تسویه: {str(e)}')
            logger.error(f"Settlement approval error: {e}", exc_info=True)

    return redirect(reverse('dashboard:settlements_list'))


# ═══════════════════════════════════════════════
#   رد تسویه
# ═══════════════════════════════════════════════
@role_required('financial_admin', 'super_admin')
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
        settlement.rejection_reason = reason
        settlement.save(update_fields=['status', 'rejection_reason'])

        DashboardCacheService.invalidate_dashboard_stats()
        DashboardAuditService.log_settlement_rejected(request, settlement, reason)

        messages.warning(
            request,
            f'تسویه کسب‌وکار "{settlement.business.name}" رد شد.'
        )

        # ✅ FIX ۳.۳.۶: ارسال اعلان به صاحب کسب‌وکار
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                user=settlement.business.owner,
                type='system',
                title='تسویه حساب رد شد ❌',
                body=(
                    f'درخواست تسویه به مبلغ {settlement.amount:,} تومان '
                    f'رد شد. دلیل: {reason}'
                ),
                data={
                    'settlement_id': settlement.id,
                    'reason': reason,
                },
                channels=['in_app'],
            )
        except Exception as e:
            logger.error(f"Failed to send settlement rejection notification: {e}")

    return redirect(reverse('dashboard:settlements_list'))