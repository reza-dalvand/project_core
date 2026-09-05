# apps/dashboard/views/users.py
"""
مدیریت کاربران — لیست، جستجو، فیلتر، جزئیات، فعال/غیرفعال
✅ فاز ۳: رفع ۵ باگ
- ۳.۱.۱: اعتبارسنجی شماره تلفن در user_create_view
- ۳.۱.۲: جلوگیری از تغییر is_staff سوپریوزر
- ۳.۱.۳: بررسی کسب‌وکار فعال قبل از حذف
- ۳.۱.۴: بهینه‌سازی کوئری‌های user_detail_view
- ۳.۱.۵: فیلتر business_owner با Exists
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Exists, OuterRef
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from apps.dashboard.decorators import admin_login_required, role_required
from apps.core.validators import validate_iranian_phone

logger = logging.getLogger(__name__)

User = get_user_model()


@admin_login_required
def users_list_view(request):
    """لیست کاربران با جستجو و فیلتر"""
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page_number = request.GET.get('page', 1)

    try:
        queryset = User.objects.filter(is_active=True).annotate(
            businesses_count=Count(
                'businesses', filter=Q(businesses__is_active=True)
            ),
            appointments_count=Count(
                'appointments', filter=Q(appointments__is_active=True)
            ),
        ).order_by('-date_joined')
    except DatabaseError as e:
        logger.error(f"Users list DB error: {e}")
        messages.error(request, 'خطا در دریافت لیست کاربران.')
        queryset = User.objects.none()

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
        # ✅ FIX ۳.۱.۵: استفاده از Exists به جای distinct()
        # قبلاً: queryset.filter(businesses__isnull=False).distinct()
        # مشکل: با annotate تداخل داشت و نتایج تکراری می‌داد
        from apps.businesses.models import Business
        queryset = queryset.filter(
            Exists(
                Business.objects.filter(
                    owner=OuterRef('pk'),
                    is_active=True,
                )
            )
        )

    # صفحه‌بندی
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    # آمار سریع
    try:
        stats = {
            'total': User.objects.count(),
            'active': User.objects.filter(
                is_active=True, is_verified=True
            ).count(),
            'inactive': User.objects.filter(is_active=False).count(),
            'unverified': User.objects.filter(is_verified=False).count(),
            'staff': User.objects.filter(is_staff=True).count(),
        }
    except DatabaseError:
        stats = {
            'total': 0, 'active': 0, 'inactive': 0,
            'unverified': 0, 'staff': 0,
        }

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'stats': stats,
    }
    return render(request, 'dashboard/users/list.html', context)


# ═══════════════════════════════════════════════
#   ایجاد کاربر
# ═══════════════════════════════════════════════
@role_required('super_admin', 'app_admin')
@admin_login_required
def user_create_view(request):
    """ایجاد کاربر جدید از پنل ادمین"""
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        is_verified = request.POST.get('is_verified') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'

        # ✅ FIX ۳.۱.۱: اعتبارسنجی شماره تلفن با هندل کامل خطا
        try:
            phone = validate_iranian_phone(phone)
        except ValidationError as e:
            message = (
                e.messages[0]
                if hasattr(e, 'messages') and e.messages
                else 'شماره موبایل معتبر نیست'
            )
            messages.error(request, message)
            return render(request, 'dashboard/users/create.html', {
                'phone': phone,
                'first_name': first_name,
                'last_name': last_name,
            })
        except Exception as e:
            logger.error(f"Phone validation error: {e}")
            messages.error(request, 'خطا در اعتبارسنجی شماره تلفن.')
            return render(request, 'dashboard/users/create.html', {
                'phone': phone,
                'first_name': first_name,
                'last_name': last_name,
            })

        # بررسی تکراری نبودن
        if User.objects.filter(phone=phone).exists():
            messages.error(
                request,
                f'کاربری با شماره {phone} قبلاً ثبت شده است.'
            )
            return render(request, 'dashboard/users/create.html', {
                'phone': phone,
                'first_name': first_name,
                'last_name': last_name,
            })

        # ایجاد کاربر
        try:
            user = User.objects.create_user(
                phone=phone,
                first_name=first_name,
                last_name=last_name,
                is_verified=is_verified,
                is_staff=is_staff,
            )
            logger.info(
                f"Admin created user: {phone} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(
                request,
                f'کاربر {phone} با موفقیت ایجاد شد.'
            )
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )
        except Exception as e:
            logger.error(f"User create error: {e}", exc_info=True)
            messages.error(request, 'خطا در ایجاد کاربر.')

    return render(request, 'dashboard/users/create.html')


# ═══════════════════════════════════════════════
#   ویرایش کاربر
# ═══════════════════════════════════════════════
@role_required('super_admin', 'app_admin')
@admin_login_required
def user_edit_view(request, user_id):
    """ویرایش اطلاعات کاربر"""
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        national_id = request.POST.get('national_id', '').strip()
        is_verified = request.POST.get('is_verified') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        # جلوگیری از غیرفعال کردن خودتان
        admin_phone = request.session.get('dashboard_admin_phone')
        if user.phone == admin_phone and not is_active:
            messages.error(
                request,
                'نمی‌توانید حساب خودتان را غیرفعال کنید.'
            )
            return redirect(
                reverse('dashboard:user_edit', kwargs={'user_id': user.id})
            )

        # جلوگیری از تغییر وضعیت سوپریوزر
        if user.is_superuser and not is_active:
            messages.error(
                request,
                'نمی‌توانید حساب سوپرادمین را غیرفعال کنید.'
            )
            return redirect(
                reverse('dashboard:user_edit', kwargs={'user_id': user.id})
            )

        # ✅ FIX ۳.۱.۲: جلوگیری از تغییر is_staff سوپریوزر
        if user.is_superuser and not is_staff:
            messages.error(
                request,
                'نمی‌توانید دسترسی ادمین سوپریوزر را تغییر دهید.'
            )
            return redirect(
                reverse('dashboard:user_edit', kwargs={'user_id': user.id})
            )

        # ✅ FIX ۳.۱.۲: جلوگیری از غیرفعال کردن خودتان
        if user.phone == admin_phone and not is_active:
            messages.error(
                request,
                'نمی‌توانید حساب خودتان را غیرفعال کنید.'
            )
            return redirect(
                reverse('dashboard:user_edit', kwargs={'user_id': user.id})
            )

        try:
            user.first_name = first_name
            user.last_name = last_name
            user.national_id = national_id
            user.is_verified = is_verified
            user.is_staff = is_staff
            user.is_active = is_active
            user.save(update_fields=[
                'first_name', 'last_name', 'national_id',
                'is_verified', 'is_staff', 'is_active',
            ])
            logger.info(
                f"Admin edited user {user.id} "
                f"by {admin_phone}"
            )
            messages.success(
                request,
                f'اطلاعات کاربر {user.phone} بروزرسانی شد.'
            )
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )
        except Exception as e:
            logger.error(f"User edit error: {e}", exc_info=True)
            messages.error(request, 'خطا در بروزرسانی کاربر.')

    context = {
        'user_obj': user,
    }
    return render(request, 'dashboard/users/edit.html', context)


# ═══════════════════════════════════════════════
#   حذف کاربر (نرم)
# ═══════════════════════════════════════════════
@role_required('super_admin')
@admin_login_required
def user_delete_view(request, user_id):
    """حذف نرم کاربر — فقط سوپر ادمین"""
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        # تأیید سمت سرور
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )

        admin_phone = request.session.get('dashboard_admin_phone')

        # جلوگیری از حذف خودتان
        if user.phone == admin_phone:
            messages.error(
                request, 'نمی‌توانید حساب خودتان را حذف کنید.'
            )
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )

        # جلوگیری از حذف سوپریوزر
        if user.is_superuser:
            messages.error(
                request, 'نمی‌توانید حساب سوپرادمین را حذف کنید.'
            )
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )

        # جلوگیری از حذف کاربر با نوبت فعال
        active_appointments = user.appointments.filter(
            status='reserved', is_active=True
        ).count()
        if active_appointments > 0:
            messages.error(
                request,
                f'این کاربر {active_appointments} نوبت فعال دارد. '
                f'ابتدا نوبت‌ها را لغو کنید.'
            )
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )

        # ✅ FIX ۳.۱.۳: بررسی کسب‌وکار فعال با نوبت‌های آینده
        from apps.businesses.models import Business
        active_businesses = Business.objects.filter(
            owner=user, is_active=True
        ).count()
        if active_businesses > 0:
            messages.error(
                request,
                f'این کاربر {active_businesses} کسب‌وکار فعال دارد. '
                f'ابتدا کسب‌وکارها را غیرفعال کنید.'
            )
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )

        try:
            phone = user.phone
            user.is_active = False
            user.is_verified = False
            user.first_name = ''
            user.last_name = ''
            user.national_id = ''
            user.avatar = None
            user.save(update_fields=[
                'is_active', 'is_verified', 'first_name',
                'last_name', 'national_id', 'avatar',
            ])
            logger.info(
                f"Admin soft-deleted user {phone} "
                f"by {admin_phone}"
            )
            messages.success(request, f'کاربر {phone} حذف شد.')
            return redirect(reverse('dashboard:users_list'))
        except Exception as e:
            logger.error(f"User delete error: {e}", exc_info=True)
            messages.error(request, 'خطا در حذف کاربر.')

    return redirect(
        reverse('dashboard:user_detail', kwargs={'user_id': user.id})
    )


# ═══════════════════════════════════════════════
#   ارسال نوتیفیکیشن به کاربر
# ═══════════════════════════════════════════════
@role_required('super_admin', 'app_admin', 'support_admin')
@admin_login_required
def user_notify_view(request, user_id):
    """ارسال نوتیفیکیشن به کاربر"""
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()

        if not title or not body:
            messages.error(request, 'عنوان و متن نوتیفیکیشن الزامی است.')
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )

        if len(title) > 200:
            messages.error(request, 'عنوان نباید بیشتر از ۲۰۰ کاراکتر باشد.')
            return redirect(
                reverse('dashboard:user_detail', kwargs={'user_id': user.id})
            )

        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                user=user,
                type='system',
                title=title,
                body=body,
                data={
                    'sent_by': request.session.get('dashboard_admin_phone'),
                },
                channels=['in_app'],
            )
            logger.info(
                f"Admin sent notification to user {user.id} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )
            messages.success(
                request,
                f'نوتیفیکیشن برای {user.phone} ارسال شد.'
            )
        except Exception as e:
            logger.error(f"Send notification error: {e}", exc_info=True)
            messages.error(request, 'خطا در ارسال نوتیفیکیشن.')

    return redirect(
        reverse('dashboard:user_detail', kwargs={'user_id': user.id})
    )


# ═══════════════════════════════════════════════
#   جزئیات کاربر
# ═══════════════════════════════════════════════
@admin_login_required
def user_detail_view(request, user_id):
    """جزئیات کاربر + اطلاعات بانکی + دستگاه‌ها"""
    try:
        user = get_object_or_404(
            User.objects.prefetch_related(
                'businesses', 'appointments', 'devices',
            ),
            id=user_id,
        )
    except Exception as e:
        logger.error(f"User detail error: {e}")
        messages.error(request, 'خطا در دریافت جزئیات کاربر.')
        return redirect(reverse('dashboard:users_list'))

    # ✅ FIX ۳.۱.۴: آمار کاربر در یک کوئری با annotate
    try:
        from apps.businesses.models import Business
        from apps.appointments.models import Appointment
        from apps.payments.models import Transaction
        from apps.reviews.models import Review
        from apps.favorites.models import FavoriteBusiness

        user_stats = {
            'businesses_count': Business.objects.filter(
                owner=user, is_active=True
            ).count(),
            'appointments_count': Appointment.objects.filter(
                customer=user, is_active=True
            ).count(),
            'transactions_count': Transaction.objects.filter(
                customer=user, is_active=True
            ).count(),
            'reviews_count': Review.objects.filter(
                customer=user, is_active=True
            ).count(),
            'favorites_count': FavoriteBusiness.objects.filter(
                user=user, is_active=True
            ).count(),
        }
    except DatabaseError:
        user_stats = {
            'businesses_count': 0, 'appointments_count': 0,
            'transactions_count': 0, 'reviews_count': 0,
            'favorites_count': 0,
        }

    # اطلاعات بانکی
    bank_info = None
    try:
        bank_info = getattr(user, 'bank_info', None)
    except Exception:
        pass

    # دستگاه‌های فعال
    devices = user.devices.order_by('-last_active')[:10]

    # کسب‌وکارهای کاربر
    user_businesses = user.businesses.all()

    # نوبت‌های اخیر
    recent_appointments = user.appointments.select_related(
        'business', 'service'
    ).order_by('-created_at')[:5]

    context = {
        'user_obj': user,
        'user_stats': user_stats,
        'bank_info': bank_info,
        'devices': devices,
        'user_businesses': user_businesses,
        'recent_appointments': recent_appointments,
    }
    return render(request, 'dashboard/users/detail.html', context)


# ═══════════════════════════════════════════════
#   فعال/غیرفعال کردن کاربر
# ═══════════════════════════════════════════════
@admin_login_required
def user_toggle_active_view(request, user_id):
    """فعال/غیرفعال کردن کاربر"""
    user = get_object_or_404(User, id=user_id)

    # جلوگیری از غیرفعال کردن خودتان
    admin_phone = request.session.get('dashboard_admin_phone')
    if user.phone == admin_phone:
        messages.error(request, 'نمی‌توانید حساب خودتان را غیرفعال کنید.')
        return redirect(
            reverse('dashboard:user_detail', kwargs={'user_id': user.id})
        )

    # جلوگیری از غیرفعال کردن سوپرادمین
    if user.is_superuser:
        messages.error(request, 'نمی‌توانید حساب سوپرادمین را غیرفعال کنید.')
        return redirect(
            reverse('dashboard:user_detail', kwargs={'user_id': user.id})
        )

    if request.method == 'POST':
        try:
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
            status_text = 'فعال' if user.is_active else 'غیرفعال'
            messages.success(request, f'کاربر {user.phone} {status_text} شد.')
            logger.info(f"Admin toggled user {user.phone} to {status_text}")
        except DatabaseError as e:
            logger.error(f"User toggle DB error: {e}")
            messages.error(
                request,
                'خطا در تغییر وضعیت کاربر. لطفاً دوباره تلاش کنید.'
            )
        except Exception as e:
            logger.error(f"User toggle unexpected error: {e}")
            messages.error(request, 'خطای غیرمنتظره در تغییر وضعیت کاربر.')

    return redirect(
        reverse('dashboard:user_detail', kwargs={'user_id': user.id})
    )