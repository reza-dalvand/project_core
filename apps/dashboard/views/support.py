"""
مدیریت پشتیبانی — تیکت‌ها، پیام‌های تماس، اعلان‌ها
✅ فاز ۳: هندل خطا
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import DatabaseError
from apps.support.models import SupportTicket
from apps.landing.models import ContactMessage
from apps.notifications.models import Notification, SMSLog
from apps.dashboard.decorators import admin_login_required

logger = logging.getLogger(__name__)


@admin_login_required
def support_index_view(request):
    """داشبورد اصلی پشتیبانی با آمار"""
    try:
        ticket_stats = SupportTicket.objects.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status=SupportTicket.Status.OPEN)),
            in_progress=Count('id', filter=Q(status=SupportTicket.Status.IN_PROGRESS)),
            resolved=Count('id', filter=Q(status=SupportTicket.Status.RESOLVED)),
            closed=Count('id', filter=Q(status=SupportTicket.Status.CLOSED)),
        )
        message_stats = ContactMessage.objects.aggregate(
            total=Count('id'),
            unread=Count('id', filter=Q(is_read=False)),
            unreplied=Count('id', filter=Q(is_replied=False)),
        )
        notification_stats = Notification.objects.aggregate(
            total=Count('id'),
            unread=Count('id', filter=Q(is_read=False)),
        )
        sms_stats = SMSLog.objects.aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status=SMSLog.Status.SENT)),
            failed=Count('id', filter=Q(status=SMSLog.Status.FAILED)),
        )
    except DatabaseError as e:
        logger.error(f"Support index DB error: {e}")
        messages.error(request, 'خطا در دریافت آمار پشتیبانی.')
        ticket_stats = {'total': 0, 'open': 0, 'in_progress': 0, 'resolved': 0, 'closed': 0}
        message_stats = {'total': 0, 'unread': 0, 'unreplied': 0}
        notification_stats = {'total': 0, 'unread': 0}
        sms_stats = {'total': 0, 'sent': 0, 'failed': 0}

    recent_tickets = SupportTicket.objects.select_related(
        'user'
    ).order_by('-created_at')[:5]

    recent_messages = ContactMessage.objects.order_by('-created_at')[:5]

    pending_tickets = SupportTicket.objects.select_related(
        'user'
    ).filter(
        status__in=[SupportTicket.Status.OPEN, SupportTicket.Status.IN_PROGRESS]
    ).order_by('priority', '-created_at')[:10]

    context = {
        'ticket_stats': ticket_stats,
        'message_stats': message_stats,
        'notification_stats': notification_stats,
        'sms_stats': sms_stats,
        'recent_tickets': recent_tickets,
        'recent_messages': recent_messages,
        'pending_tickets': pending_tickets,
    }
    return render(request, 'dashboard/support/index.html', context)


# ═══════════════════════════════════════════════
#   تیکت‌ها
# ═══════════════════════════════════════════════
@admin_login_required
def tickets_list_view(request):
    """لیست تیکت‌های پشتیبانی"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    priority_filter = request.GET.get('priority', 'all')
    page_number = request.GET.get('page', 1)

    queryset = SupportTicket.objects.filter(is_active=True).select_related(
        'user'
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(subject__icontains=search) |
            Q(message__icontains=search) |
            Q(user__phone__icontains=search)
        )

    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    if priority_filter != 'all':
        queryset = queryset.filter(priority=priority_filter)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': SupportTicket.objects.count(),
            'open': SupportTicket.objects.filter(status=SupportTicket.Status.OPEN).count(),
            'in_progress': SupportTicket.objects.filter(status=SupportTicket.Status.IN_PROGRESS).count(),
            'resolved': SupportTicket.objects.filter(status=SupportTicket.Status.RESOLVED).count(),
            'closed': SupportTicket.objects.filter(status=SupportTicket.Status.CLOSED).count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'open': 0, 'in_progress': 0, 'resolved': 0, 'closed': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'stats': stats,
        'status_choices': SupportTicket.Status.choices,
        'priority_choices': SupportTicket.Priority.choices,
    }
    return render(request, 'dashboard/support/tickets_list.html', context)


@admin_login_required
def ticket_detail_view(request, ticket_id):
    """جزئیات تیکت + پاسخ"""
    ticket = get_object_or_404(
        SupportTicket.objects.select_related('user'),
        id=ticket_id,
    )

    if request.method == 'POST':
        response_text = request.POST.get('response', '').strip()
        new_status = request.POST.get('status', ticket.status)

        # ✅ فاز ۳: هندل خطا
        try:
            if response_text:
                ticket.response = response_text
                ticket.responded_at = timezone.now()

            if new_status in dict(SupportTicket.Status.choices):
                ticket.status = new_status

            ticket.save()

            messages.success(request, 'پاسخ با موفقیت ثبت شد.')
            logger.info(f"Ticket {ticket_id} responded by admin")

        except DatabaseError as e:
            logger.error(f"Ticket update DB error: {e}")
            messages.error(request, 'خطا در ثبت پاسخ. لطفاً دوباره تلاش کنید.')
        except Exception as e:
            logger.error(f"Ticket update unexpected error: {e}")
            messages.error(request, 'خطای غیرمنتظره در ثبت پاسخ.')

        return redirect(reverse('dashboard:ticket_detail', kwargs={'ticket_id': ticket_id}))

    context = {
        'ticket': ticket,
        'status_choices': SupportTicket.Status.choices,
    }
    return render(request, 'dashboard/support/ticket_detail.html', context)


# ═══════════════════════════════════════════════
#   پیام‌های تماس
# ═══════════════════════════════════════════════
@admin_login_required
def messages_list_view(request):
    """لیست پیام‌های تماس"""
    search = request.GET.get('search', '').strip()
    read_filter = request.GET.get('read', 'all')
    page_number = request.GET.get('page', 1)

    queryset = ContactMessage.objects.order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(subject__icontains=search) |
            Q(message__icontains=search)
        )

    if read_filter == 'unread':
        queryset = queryset.filter(is_read=False)
    elif read_filter == 'read':
        queryset = queryset.filter(is_read=True)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': ContactMessage.objects.count(),
            'unread': ContactMessage.objects.filter(is_read=False).count(),
            'replied': ContactMessage.objects.filter(is_replied=True).count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'unread': 0, 'replied': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'read_filter': read_filter,
        'stats': stats,
    }
    return render(request, 'dashboard/support/messages_list.html', context)


@admin_login_required
def message_detail_view(request, message_id):
    """جزئیات پیام تماس"""
    message = get_object_or_404(ContactMessage, id=message_id)

    # علامت‌گذاری به عنوان خوانده شده
    if not message.is_read:
        try:
            message.is_read = True
            message.save(update_fields=['is_read'])
        except Exception as e:
            logger.error(f"Message read update error: {e}")

    if request.method == 'POST':
        # ✅ فاز ۳: هندل خطا
        try:
            admin_note = request.POST.get('admin_note', '').strip()
            is_replied = request.POST.get('is_replied', '') == 'on'

            if admin_note:
                message.admin_note = admin_note

            message.is_replied = is_replied
            message.save()

            messages.success(request, 'پیام بروزرسانی شد.')

        except DatabaseError as e:
            logger.error(f"Message update DB error: {e}")
            messages.error(request, 'خطا در بروزرسانی پیام.')
        except Exception as e:
            logger.error(f"Message update unexpected error: {e}")
            messages.error(request, 'خطای غیرمنتظره در بروزرسانی پیام.')

        return redirect(reverse('dashboard:message_detail', kwargs={'message_id': message_id}))

    context = {
        'message': message,
    }
    return render(request, 'dashboard/support/message_detail.html', context)


# ═══════════════════════════════════════════════
#   اعلان‌ها
# ═══════════════════════════════════════════════
@admin_login_required
def notifications_list_view(request):
    """لیست اعلان‌ها"""
    search = request.GET.get('search', '').strip()
    type_filter = request.GET.get('type', 'all')
    page_number = request.GET.get('page', 1)

    queryset = Notification.objects.select_related(
        'user'
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(body__icontains=search) |
            Q(user__phone__icontains=search)
        )

    if type_filter != 'all':
        queryset = queryset.filter(type=type_filter)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': Notification.objects.count(),
            'unread': Notification.objects.filter(is_read=False).count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'unread': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'type_filter': type_filter,
        'stats': stats,
        'type_choices': Notification.Type.choices,
    }
    return render(request, 'dashboard/support/notifications_list.html', context)


@admin_login_required
def sms_logs_view(request):
    """لیست لاگ پیامک‌ها"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page_number = request.GET.get('page', 1)

    queryset = SMSLog.objects.select_related(
        'user', 'template'
    ).order_by('-sent_at')

    if search:
        queryset = queryset.filter(
            Q(phone__icontains=search) |
            Q(message__icontains=search)
        )

    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': SMSLog.objects.count(),
            'sent': SMSLog.objects.filter(status=SMSLog.Status.SENT).count(),
            'delivered': SMSLog.objects.filter(status=SMSLog.Status.DELIVERED).count(),
            'failed': SMSLog.objects.filter(status=SMSLog.Status.FAILED).count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'sent': 0, 'delivered': 0, 'failed': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'stats': stats,
        'status_choices': SMSLog.Status.choices,
    }
    return render(request, 'dashboard/support/sms_logs.html', context)