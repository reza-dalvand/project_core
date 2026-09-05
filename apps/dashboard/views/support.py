# apps/dashboard/views/support.py
"""
مدیریت پشتیبانی — تیکت‌ها، پیام‌های تماس، اعلان‌ها
✅ فاز ۳: رفع ۵ باگ
- ۳.۵.۱: اعتبارسنجی انتقال وضعیت تیکت
- ۳.۵.۲: حذف علامت‌گذاری خودکار خوانده‌شده
- ۳.۵.۳: محدودیت طول متن نوتیفیکیشن
- ۳.۵.۴: هندل خطای ارسال پیامک
- ۳.۵.۵: اعتبارسنجی وضعیت در تغییر دسته‌ای
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
from apps.dashboard.decorators import admin_login_required, role_required

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۵.۱: قوانین انتقال وضعیت تیکت
# ═══════════════════════════════════════════════
VALID_TICKET_TRANSITIONS = {
    SupportTicket.Status.OPEN: [
        SupportTicket.Status.IN_PROGRESS,
        SupportTicket.Status.RESOLVED,
        SupportTicket.Status.CLOSED,
    ],
    SupportTicket.Status.IN_PROGRESS: [
        SupportTicket.Status.RESOLVED,
        SupportTicket.Status.CLOSED,
        SupportTicket.Status.OPEN,
    ],
    SupportTicket.Status.RESOLVED: [
        SupportTicket.Status.CLOSED,
        SupportTicket.Status.OPEN,
    ],
    SupportTicket.Status.CLOSED: [
        SupportTicket.Status.OPEN,
    ],
}

# ✅ FIX ۳.۵.۳: حداکثر طول متن نوتیفیکیشن
MAX_NOTIFICATION_BODY_LENGTH = 1000


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
            replied=Count('id', filter=Q(is_replied=True)),
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
        message_stats = {'total': 0, 'unread': 0, 'replied': 0}
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


@role_required('support_admin', 'super_admin')
@admin_login_required
def ticket_create_view(request):
    """ایجاد تیکت پشتیبانی از ادمین"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == 'POST':
        user_phone = request.POST.get('user_phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()
        priority = request.POST.get('priority', 'medium')

        if not user_phone:
            messages.error(request, 'شماره تلفن کاربر الزامی است.')
            return redirect(reverse('dashboard:ticket_create'))

        try:
            user = User.objects.get(phone=user_phone)
        except User.DoesNotExist:
            messages.error(request, 'کاربری با این شماره تلفن یافت نشد.')
            return redirect(reverse('dashboard:ticket_create'))

        if not subject or len(subject) < 3:
            messages.error(request, 'موضوع تیکت باید حداقل ۳ کاراکتر باشد.')
            return redirect(reverse('dashboard:ticket_create'))

        if not message_text or len(message_text) < 10:
            messages.error(request, 'متن پیام باید حداقل ۱۰ کاراکتر باشد.')
            return redirect(reverse('dashboard:ticket_create'))

        if priority not in dict(SupportTicket.Priority.choices):
            messages.error(request, 'اولویت نامعتبر است.')
            return redirect(reverse('dashboard:ticket_create'))

        try:
            ticket = SupportTicket.objects.create(
                user=user,
                subject=subject,
                message=message_text,
                priority=priority,
            )
            logger.info(
                f"Admin created ticket {ticket.id} for {user.phone} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(request, 'تیکت با موفقیت ایجاد شد.')
            return redirect(
                reverse('dashboard:ticket_detail', kwargs={'ticket_id': ticket.id})
            )
        except Exception as e:
            logger.error(f"Ticket create error: {e}", exc_info=True)
            messages.error(request, 'خطا در ایجاد تیکت.')

    context = {
        'priority_choices': SupportTicket.Priority.choices,
    }
    return render(request, 'dashboard/support/ticket_create.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۵.۱: جزئیات تیکت با اعتبارسنجی انتقال وضعیت
# ═══════════════════════════════════════════════
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

        if new_status not in dict(SupportTicket.Status.choices):
            messages.error(request, 'وضعیت نامعتبر است.')
            return redirect(
                reverse('dashboard:ticket_detail', kwargs={'ticket_id': ticket_id})
            )

        # ✅ FIX ۳.۵.۱: اعتبارسنجی انتقال وضعیت
        allowed_transitions = VALID_TICKET_TRANSITIONS.get(
            ticket.status, []
        )
        if new_status != ticket.status and new_status not in allowed_transitions:
            current_display = dict(
                SupportTicket.Status.choices
            ).get(ticket.status, ticket.status)
            new_display = dict(
                SupportTicket.Status.choices
            ).get(new_status, new_status)
            messages.error(
                request,
                f'تغییر وضعیت از «{current_display}» '
                f'به «{new_display}» مجاز نیست.'
            )
            return redirect(
                reverse('dashboard:ticket_detail', kwargs={'ticket_id': ticket_id})
            )

        try:
            if response_text:
                ticket.response = response_text
                ticket.responded_at = timezone.now()
            ticket.status = new_status
            ticket.save()
            messages.success(request, 'تیکت با موفقیت بروزرسانی شد.')
            logger.info(
                f"Ticket {ticket_id} updated: status={new_status}, "
                f"responded={bool(response_text)}"
            )
        except DatabaseError as e:
            logger.error(f"Ticket update DB error: {e}")
            messages.error(request, 'خطا در بروزرسانی تیکت.')
        except Exception as e:
            logger.error(f"Ticket update unexpected error: {e}")
            messages.error(request, 'خطای غیرمنتظره در بروزرسانی تیکت.')

        return redirect(
            reverse('dashboard:ticket_detail', kwargs={'ticket_id': ticket_id})
        )

    context = {
        'ticket': ticket,
        'status_choices': SupportTicket.Status.choices,
    }
    return render(request, 'dashboard/support/ticket_detail.html', context)


@role_required('support_admin', 'super_admin')
@admin_login_required
def ticket_delete_view(request, ticket_id):
    """حذف تیکت پشتیبانی"""
    ticket = get_object_or_404(SupportTicket, id=ticket_id)

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:tickets_list'))

        try:
            subject_preview = ticket.subject[:30]
            ticket.is_active = False
            ticket.save(update_fields=['is_active'])
            logger.info(
                f"Admin soft-deleted ticket {ticket_id} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(request, f'تیکت "{subject_preview}" حذف شد.')
        except Exception as e:
            logger.error(f"Ticket delete error: {e}")
            messages.error(request, 'خطا در حذف تیکت.')

    return redirect(reverse('dashboard:tickets_list'))


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۵.۵: تغییر وضعیت دسته‌ای با اعتبارسنجی کامل
# ═══════════════════════════════════════════════
@role_required('support_admin', 'super_admin')
@admin_login_required
def ticket_bulk_status_view(request):
    """تغییر وضعیت دسته‌ای تیکت‌ها"""
    if request.method == 'POST':
        ticket_ids = request.POST.getlist('ticket_ids')
        new_status = request.POST.get('new_status', '')

        if not ticket_ids:
            messages.error(request, 'هیچ تیکتی انتخاب نشده است.')
            return redirect(reverse('dashboard:tickets_list'))

        # ✅ FIX ۳.۵.۵: اعتبارسنجی وضعیت جدید
        if new_status not in dict(SupportTicket.Status.choices):
            messages.error(
                request,
                f'وضعیت "{new_status}" نامعتبر است. '
                f'وضعیت‌های مجاز: '
                + '، '.join(dict(SupportTicket.Status.choices).values())
            )
            return redirect(reverse('dashboard:tickets_list'))

        # محدودیت تعداد
        if len(ticket_ids) > 100:
            messages.error(
                request,
                'حداکثر ۱۰۰ تیکت در هر عملیات دسته‌ای مجاز است.'
            )
            return redirect(reverse('dashboard:tickets_list'))

        try:
            updated_count = SupportTicket.objects.filter(
                id__in=ticket_ids,
                is_active=True,
            ).update(status=new_status)
            messages.success(
                request,
                f'{updated_count} تیکت به وضعیت '
                f'"{dict(SupportTicket.Status.choices)[new_status]}" تغییر یافت.'
            )
            logger.info(
                f"Admin bulk-updated {updated_count} tickets "
                f"to {new_status} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
        except Exception as e:
            logger.error(f"Ticket bulk status error: {e}")
            messages.error(request, 'خطا در تغییر وضعیت دسته‌ای.')

    return redirect(reverse('dashboard:tickets_list'))


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


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۵.۲: جزئیات پیام بدون علامت‌گذاری خودکار
# ═══════════════════════════════════════════════
@admin_login_required
def message_detail_view(request, message_id):
    """جزئیات پیام تماس"""
    message = get_object_or_404(ContactMessage, id=message_id)

    if request.method == 'POST':
        action = request.POST.get('action', 'update')

        try:
            if action == 'mark_read':
                message.is_read = not message.is_read
                message.save(update_fields=['is_read'])
                status_text = 'خوانده شده' if message.is_read else 'خوانده نشده'
                messages.success(request, f'پیام به عنوان {status_text} علامت‌گذاری شد.')

            elif action == 'update':
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

        return redirect(
            reverse('dashboard:message_detail', kwargs={'message_id': message_id})
        )

    context = {
        'message': message,
    }
    return render(request, 'dashboard/support/message_detail.html', context)


@role_required('support_admin', 'super_admin')
@admin_login_required
def message_delete_view(request, message_id):
    """حذف پیام تماس"""
    message = get_object_or_404(ContactMessage, id=message_id)

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:messages_list'))

        try:
            subject_preview = message.subject[:30]
            message.is_active = False
            message.save(update_fields=['is_active'])
            logger.info(
                f"Admin soft-deleted contact message {message_id} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(request, f'پیام "{subject_preview}" حذف شد.')
        except Exception as e:
            logger.error(f"Message delete error: {e}")
            messages.error(request, 'خطا در حذف پیام.')

    return redirect(reverse('dashboard:messages_list'))


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


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۵.۳: ارسال نوتیفیکیشن با محدودیت طول
# ═══════════════════════════════════════════════
@role_required('support_admin', 'super_admin')
@admin_login_required
def notification_create_view(request):
    """ارسال نوتیفیکیشن به کاربر"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == 'POST':
        user_phone = request.POST.get('user_phone', '').strip()
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        notif_type = request.POST.get('type', 'system')

        if not user_phone:
            messages.error(request, 'شماره تلفن کاربر الزامی است.')
            return redirect(reverse('dashboard:notification_create'))

        try:
            user = User.objects.get(phone=user_phone)
        except User.DoesNotExist:
            messages.error(request, 'کاربری با این شماره تلفن یافت نشد.')
            return redirect(reverse('dashboard:notification_create'))

        if not title or len(title) > 200:
            messages.error(request, 'عنوان الزامی است و حداکثر ۲۰۰ کاراکتر.')
            return redirect(reverse('dashboard:notification_create'))

        if not body:
            messages.error(request, 'متن اعلان الزامی است.')
            return redirect(reverse('dashboard:notification_create'))

        # ✅ FIX ۳.۵.۳: محدودیت طول متن
        if len(body) > MAX_NOTIFICATION_BODY_LENGTH:
            messages.error(
                request,
                f'متن اعلان نباید بیشتر از '
                f'{MAX_NOTIFICATION_BODY_LENGTH} کاراکتر باشد.'
            )
            return redirect(reverse('dashboard:notification_create'))

        if notif_type not in dict(Notification.Type.choices):
            messages.error(request, 'نوع اعلان نامعتبر است.')
            return redirect(reverse('dashboard:notification_create'))

        try:
            notification = Notification.objects.create(
                user=user,
                type=notif_type,
                title=title,
                body=body,
                data={
                    'sent_by': request.session.get('dashboard_admin_phone'),
                    'sent_via': 'dashboard',
                },
            )
            logger.info(
                f"Admin sent notification {notification.id} to {user.phone} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(
                request,
                f'اعلان برای {user.phone} ارسال شد.'
            )
            return redirect(reverse('dashboard:notifications_list'))

        except Exception as e:
            logger.error(f"Notification create error: {e}", exc_info=True)
            messages.error(request, 'خطا در ارسال اعلان.')

    context = {
        'type_choices': Notification.Type.choices,
    }
    return render(request, 'dashboard/support/notification_create.html', context)


@role_required('support_admin', 'super_admin')
@admin_login_required
def notification_delete_view(request, notification_id):
    """حذف اعلان"""
    notification = get_object_or_404(Notification, id=notification_id)

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:notifications_list'))

        try:
            title_preview = notification.title[:30]
            notification.delete()
            logger.info(
                f"Admin deleted notification {notification_id} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(request, f'اعلان "{title_preview}" حذف شد.')
        except Exception as e:
            logger.error(f"Notification delete error: {e}")
            messages.error(request, 'خطا در حذف اعلان.')

    return redirect(reverse('dashboard:notifications_list'))


# ═══════════════════════════════════════════════
#   لاگ پیامک‌ها
# ═══════════════════════════════════════════════
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


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۵.۴: ارسال پیامک با هندل خطای کامل
# ═══════════════════════════════════════════════
@role_required('support_admin', 'super_admin')
@admin_login_required
def sms_send_view(request):
    """ارسال پیامک به کاربر"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == 'POST':
        user_phone = request.POST.get('user_phone', '').strip()
        message_text = request.POST.get('message', '').strip()

        if not user_phone:
            messages.error(request, 'شماره تلفن الزامی است.')
            return redirect(reverse('dashboard:sms_send'))

        if not message_text:
            messages.error(request, 'متن پیامک الزامی است.')
            return redirect(reverse('dashboard:sms_send'))

        if len(message_text) > 500:
            messages.error(request, 'متن پیامک حداکثر ۵۰۰ کاراکتر.')
            return redirect(reverse('dashboard:sms_send'))

        try:
            user = User.objects.get(phone=user_phone)
        except User.DoesNotExist:
            messages.error(request, 'کاربری با این شماره تلفن یافت نشد.')
            return redirect(reverse('dashboard:sms_send'))

        try:
            from shared.sms import get_sms_provider
            provider = get_sms_provider()
            result = provider.send(
                phone=user_phone,
                message=message_text,
                sender='بیو کلاب',
            )

            if result.success:
                SMSLog.objects.create(
                    user=user,
                    phone=user_phone,
                    message=message_text,
                    status=SMSLog.Status.SENT,
                    provider_message_id=result.message_id or '',
                    cost=result.cost,
                )
                messages.success(
                    request,
                    f'پیامک برای {user_phone} ارسال شد.'
                )
                logger.info(
                    f"Admin sent SMS to {user_phone} "
                    f"by {request.session.get('dashboard_admin_phone')}"
                )
            else:
                SMSLog.objects.create(
                    user=user,
                    phone=user_phone,
                    message=message_text,
                    status=SMSLog.Status.FAILED,
                    error_message=result.error_message,
                )
                messages.error(
                    request,
                    f'خطا در ارسال پیامک: {result.error_message}'
                )

        except ImportError:
            messages.error(request, 'سرویس پیامک در دسترس نیست.')
        except Exception as e:
            logger.error(f"SMS send error: {e}", exc_info=True)
            messages.error(request, 'خطا در ارسال پیامک.')

    return render(request, 'dashboard/support/sms_send.html')