# apps/dashboard/views/bookings.py
"""
مدیریت نوبت‌ها، خدمات و زمان‌بندی‌ها — داشبورد ادمین
✅ فاز ۳: رفع ۳ باگ
- ۳.۷.۱: هندل خطای استرداد وجه در appointment_cancel_view
- ۳.۷.۲: بررسی نوبت‌های آینده قبل از غیرفعال‌سازی خدمت
- ۳.۷.۳: فیلتر بازه زمانی در schedules_list_view
"""
import logging
import jdatetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import DatabaseError, transaction as db_transaction
from apps.appointments.models import Appointment
from apps.services.models import Service
from apps.schedules.models import ServiceSchedule
from apps.dashboard.decorators import admin_login_required, role_required
from apps.dashboard.services.audit_service import DashboardAuditService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#   داشبورد اصلی نوبت‌ها و خدمات
# ═══════════════════════════════════════════════
@admin_login_required
def bookings_index_view(request):
    """داشبورد اصلی نوبت‌ها و خدمات"""
    try:
        appointments_stats = Appointment.objects.filter(is_active=True).aggregate(
            total=Count('id'),
            reserved=Count('id', filter=Q(status=Appointment.Status.RESERVED)),
            done=Count('id', filter=Q(status=Appointment.Status.DONE)),
            cancelled=Count('id', filter=Q(
                status__in=[
                    Appointment.Status.CANCELLED_BY_SALON,
                    Appointment.Status.CANCELLED_BY_CUSTOMER,
                ]
            )),
        )

        services_stats = Service.objects.filter(is_active=True).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            with_deposit=Count('id', filter=Q(has_deposit=True)),
        )

        schedules_stats = ServiceSchedule.objects.filter(is_active=True).aggregate(
            total=Count('id'),
        )

        financial_stats = Appointment.objects.filter(
            is_active=True,
            status=Appointment.Status.RESERVED,
        ).aggregate(
            total_deposit=Sum('deposit_amount'),
            total_remaining=Sum('remaining_amount'),
        )

    except DatabaseError as e:
        logger.error(f"Bookings index DB error: {e}")
        messages.error(request, 'خطا در دریافت آمار نوبت‌ها.')
        appointments_stats = {
            'total': 0, 'reserved': 0, 'done': 0, 'cancelled': 0,
        }
        services_stats = {'total': 0, 'active': 0, 'with_deposit': 0}
        schedules_stats = {'total': 0}
        financial_stats = {'total_deposit': 0, 'total_remaining': 0}

    today = jdatetime.date.today()
    today_key = f'{today.year}/{today.month:02d}/{today.day:02d}'

    today_appointments = Appointment.objects.filter(
        date_key=today_key,
        status=Appointment.Status.RESERVED,
        is_active=True,
    ).select_related('customer', 'business', 'service').order_by('time_slot')[:10]

    recent_appointments = Appointment.objects.select_related(
        'customer', 'business', 'service',
    ).order_by('-created_at')[:5]

    context = {
        'appointments_stats': appointments_stats,
        'services_stats': services_stats,
        'schedules_stats': schedules_stats,
        'financial_stats': financial_stats,
        'today_appointments': today_appointments,
        'recent_appointments': recent_appointments,
        'today_key': today_key,
    }
    return render(request, 'dashboard/bookings/index.html', context)


# ═══════════════════════════════════════════════
#   لیست نوبت‌ها
# ═══════════════════════════════════════════════
@admin_login_required
def appointments_list_view(request):
    """لیست نوبت‌ها با فیلتر و جستجو"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    date_filter = request.GET.get('date_filter', 'all')
    page_number = request.GET.get('page', 1)

    queryset = Appointment.objects.filter(is_active=True).select_related(
        'customer', 'business', 'service',
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(customer__phone__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(business__name__icontains=search) |
            Q(service__name__icontains=search) |
            Q(verification_code__icontains=search)
        )

    if status_filter == 'reserved':
        queryset = queryset.filter(status=Appointment.Status.RESERVED)
    elif status_filter == 'done':
        queryset = queryset.filter(status=Appointment.Status.DONE)
    elif status_filter == 'cancelled':
        queryset = queryset.filter(
            status__in=[
                Appointment.Status.CANCELLED_BY_SALON,
                Appointment.Status.CANCELLED_BY_CUSTOMER,
            ]
        )

    today = jdatetime.date.today()
    today_key = f'{today.year}/{today.month:02d}/{today.day:02d}'

    if date_filter == 'today':
        queryset = queryset.filter(date_key=today_key)
    elif date_filter == 'week':
        week_end = today + jdatetime.timedelta(days=7)
        week_end_key = f'{week_end.year}/{week_end.month:02d}/{week_end.day:02d}'
        queryset = queryset.filter(date_key__gte=today_key, date_key__lte=week_end_key)
    elif date_filter == 'month':
        month_start_key = f'{today.year}/{today.month:02d}/01'
        month_end_day = jdatetime.jalaali_month_length(today.year, today.month)
        month_end_key = f'{today.year}/{today.month:02d}/{month_end_day:02d}'
        queryset = queryset.filter(
            date_key__gte=month_start_key, date_key__lte=month_end_key
        )

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': Appointment.objects.count(),
            'reserved': Appointment.objects.filter(
                status=Appointment.Status.RESERVED
            ).count(),
            'done': Appointment.objects.filter(
                status=Appointment.Status.DONE
            ).count(),
            'cancelled': Appointment.objects.filter(
                status__in=[
                    Appointment.Status.CANCELLED_BY_SALON,
                    Appointment.Status.CANCELLED_BY_CUSTOMER,
                ]
            ).count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'reserved': 0, 'done': 0, 'cancelled': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'stats': stats,
        'status_choices': Appointment.Status.choices,
    }
    return render(request, 'dashboard/bookings/appointments_list.html', context)


# ═══════════════════════════════════════════════
#   جزئیات نوبت
# ═══════════════════════════════════════════════
@admin_login_required
def appointment_detail_view(request, appointment_id):
    """جزئیات نوبت"""
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            'customer', 'business', 'service', 'business__owner',
        ),
        id=appointment_id,
    )

    transactions = appointment.transactions.all().order_by('-created_at')[:5]

    context = {
        'appointment': appointment,
        'transactions': transactions,
    }
    return render(request, 'dashboard/bookings/appointment_detail.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۷.۱: لغو نوبت با هندل خطای استرداد
# ═══════════════════════════════════════════════
@role_required('app_admin', 'super_admin')
@admin_login_required
def appointment_cancel_view(request, appointment_id):
    """لغو نوبت توسط ادمین"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'لغو توسط ادمین').strip()

        if not reason:
            messages.error(request, 'دلیل لغو الزامی است.')
            return redirect(
                reverse('dashboard:appointment_detail',
                        kwargs={'appointment_id': appointment_id})
            )

        if appointment.status != Appointment.Status.RESERVED:
            messages.error(request, 'این نوبت قابل لغو نیست.')
            return redirect(
                reverse('dashboard:appointment_detail',
                        kwargs={'appointment_id': appointment_id})
            )

        try:
            # ✅ FIX ۳.۷.۱: تراکنش اتمیک — اگر استرداد خطا بدهد
            # نوبت لغو نمی‌شود
            with db_transaction.atomic():
                appointment.cancel_by_salon(reason)

            DashboardAuditService.log(
                request=request,
                action='appointment.cancelled_by_admin',
                target_type='appointment',
                target_id=appointment.id,
                target_name=(
                    f'{appointment.customer.phone} - '
                    f'{appointment.service.name}'
                ),
                details={
                    'reason': reason,
                    'refund_amount': appointment.deposit_amount,
                },
                severity='warning',
            )

            messages.success(request, 'نوبت با موفقیت لغو شد.')
            logger.info(
                f"Admin cancelled appointment {appointment_id}: {reason}"
            )

        except Exception as e:
            logger.error(f"Appointment cancel error: {e}", exc_info=True)
            messages.error(
                request,
                'خطا در لغو نوبت. اگر بیعانه وجود دارد، '
                'استرداد ممکن است با مشکل مواجه شده باشد. '
                'لطفاً وضعیت تراکنش‌ها را بررسی کنید.'
            )

    return redirect(
        reverse('dashboard:appointment_detail',
                kwargs={'appointment_id': appointment_id})
    )


# ═══════════════════════════════════════════════
#   تغییر وضعیت نوبت
# ═══════════════════════════════════════════════
@role_required('app_admin', 'super_admin')
@admin_login_required
def appointment_status_change_view(request, appointment_id):
    """تغییر وضعیت نوبت"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        new_status = request.POST.get('new_status', '')

        if new_status not in dict(Appointment.Status.choices):
            messages.error(request, 'وضعیت نامعتبر است.')
            return redirect(
                reverse('dashboard:appointment_detail',
                        kwargs={'appointment_id': appointment_id})
            )

        valid_transitions = {
            Appointment.Status.RESERVED: [
                Appointment.Status.DONE,
                Appointment.Status.CANCELLED_BY_SALON,
                Appointment.Status.CANCELLED_BY_CUSTOMER,
            ],
            Appointment.Status.DONE: [],
            Appointment.Status.CANCELLED_BY_SALON: [],
            Appointment.Status.CANCELLED_BY_CUSTOMER: [],
        }

        if new_status not in valid_transitions.get(appointment.status, []):
            messages.error(
                request,
                f'تغییر وضعیت از «{appointment.get_status_display()}» '
                f'به «{dict(Appointment.Status.choices)[new_status]}» مجاز نیست.'
            )
            return redirect(
                reverse('dashboard:appointment_detail',
                        kwargs={'appointment_id': appointment_id})
            )

        try:
            appointment.status = new_status
            if new_status == Appointment.Status.DONE:
                appointment.is_verified = True
                appointment.verified_at = timezone.now()
            appointment.save()
            messages.success(request, 'وضعیت نوبت با موفقیت تغییر کرد.')
            logger.info(
                f"Admin changed appointment {appointment_id} "
                f"status to {new_status}"
            )
        except Exception as e:
            logger.error(
                f"Appointment status change error: {e}",
                exc_info=True,
            )
            messages.error(request, 'خطا در تغییر وضعیت نوبت.')

    return redirect(
        reverse('dashboard:appointment_detail',
                kwargs={'appointment_id': appointment_id})
    )


# ═══════════════════════════════════════════════
#   لیست خدمات
# ═══════════════════════════════════════════════
@admin_login_required
def services_list_view(request):
    """لیست خدمات با فیلتر و جستجو"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page_number = request.GET.get('page', 1)

    queryset = Service.objects.select_related(
        'business', 'category', 'sub_service',
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(business__name__icontains=search) |
            Q(category__name__icontains=search)
        )

    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': Service.objects.count(),
            'active': Service.objects.filter(is_active=True).count(),
            'inactive': Service.objects.filter(is_active=False).count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'active': 0, 'inactive': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'stats': stats,
    }
    return render(request, 'dashboard/bookings/services_list.html', context)


# ═══════════════════════════════════════════════
#   جزئیات خدمت
# ═══════════════════════════════════════════════
@admin_login_required
def service_detail_view(request, service_id):
    """جزئیات خدمت"""
    service = get_object_or_404(
        Service.objects.select_related(
            'business', 'category', 'sub_service', 'business__owner',
        ),
        id=service_id,
    )

    appointments_stats = Appointment.objects.filter(
        service=service,
        is_active=True,
    ).aggregate(
        total=Count('id'),
        reserved=Count('id', filter=Q(status=Appointment.Status.RESERVED)),
        done=Count('id', filter=Q(status=Appointment.Status.DONE)),
    )

    context = {
        'service': service,
        'appointments_stats': appointments_stats,
    }
    return render(request, 'dashboard/bookings/service_detail.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۷.۲: فعال/غیرفعال کردن خدمت با بررسی نوبت‌ها
# ═══════════════════════════════════════════════
@role_required('app_admin', 'super_admin')
@admin_login_required
def service_toggle_active_view(request, service_id):
    """فعال/غیرفعال کردن خدمت"""
    service = get_object_or_404(Service, id=service_id)

    if request.method == 'POST':
        # ✅ FIX ۳.۷.۲: قبل از غیرفعال‌سازی، نوبت‌های آینده بررسی شوند
        if service.is_active:
            upcoming_count = Appointment.objects.filter(
                service=service,
                status=Appointment.Status.RESERVED,
                is_active=True,
            ).count()

            if upcoming_count > 0:
                messages.error(
                    request,
                    f'این خدمت {upcoming_count} نوبت فعال دارد. '
                    f'ابتدا نوبت‌ها را لغو کنید.'
                )
                return redirect(
                    reverse('dashboard:service_detail',
                            kwargs={'service_id': service_id})
                )

        try:
            service.is_active = not service.is_active
            service.save(update_fields=['is_active'])
            status_text = 'فعال' if service.is_active else 'غیرفعال'
            messages.success(request, f'خدمت «{service.name}» {status_text} شد.')
            logger.info(
                f"Admin toggled service {service_id} to {status_text}"
            )
        except Exception as e:
            logger.error(f"Service toggle error: {e}", exc_info=True)
            messages.error(request, 'خطا در تغییر وضعیت خدمت.')

    return redirect(
        reverse('dashboard:service_detail',
                kwargs={'service_id': service_id})
    )


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۷.۳: لیست زمان‌بندی‌ها با فیلتر بازه زمانی
# ═══════════════════════════════════════════════
@admin_login_required
def schedules_list_view(request):
    """لیست زمان‌بندی‌ها با فیلتر"""
    search = request.GET.get('search', '').strip()
    date_filter = request.GET.get('date_filter', 'all')
    page_number = request.GET.get('page', 1)

    queryset = ServiceSchedule.objects.select_related(
        'business', 'service',
    ).order_by('-jy', '-jm', '-jd')

    if search:
        queryset = queryset.filter(
            Q(business__name__icontains=search) |
            Q(service__name__icontains=search) |
            Q(date_key__icontains=search)
        )

    # ✅ FIX ۳.۷.۳: فیلتر بازه زمانی
    today = jdatetime.date.today()
    today_key = f'{today.year}/{today.month:02d}/{today.day:02d}'

    if date_filter == 'today':
        queryset = queryset.filter(date_key=today_key)
    elif date_filter == 'week':
        week_end = today + jdatetime.timedelta(days=7)
        week_end_key = f'{week_end.year}/{week_end.month:02d}/{week_end.day:02d}'
        queryset = queryset.filter(
            date_key__gte=today_key, date_key__lte=week_end_key
        )
    elif date_filter == 'month':
        month_start_key = f'{today.year}/{today.month:02d}/01'
        month_end_day = jdatetime.jalaali_month_length(today.year, today.month)
        month_end_key = f'{today.year}/{today.month:02d}/{month_end_day:02d}'
        queryset = queryset.filter(
            date_key__gte=month_start_key, date_key__lte=month_end_key
        )
    elif date_filter == 'past':
        queryset = queryset.filter(date_key__lt=today_key)
    elif date_filter == 'future':
        queryset = queryset.filter(date_key__gte=today_key)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': ServiceSchedule.objects.count(),
        }
    except DatabaseError:
        stats = {'total': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'date_filter': date_filter,
        'stats': stats,
    }
    return render(request, 'dashboard/bookings/schedules_list.html', context)