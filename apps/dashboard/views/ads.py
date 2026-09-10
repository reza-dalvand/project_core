# apps/dashboard/views/ads.py
import logging
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

from apps.ads_management.models import AdBanner
from apps.businesses.models import Business
from apps.dashboard.decorators import admin_login_required, role_required

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
#   اعتبارسنجی تصویر بنر
# ═══════════════════════════════════════════════
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # ۵ مگابایت

def validate_banner_image(file_obj):
    if file_obj is None:
        return None
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f'فرمت فایل "{ext}" مجاز نیست. (jpg, png, webp, gif)')
    if file_obj.size > MAX_IMAGE_SIZE:
        raise ValueError('حجم تصویر نباید بیشتر از ۵ مگابایت باشد.')
    return file_obj

def safe_delete_file(file_field):
    if not file_field:
        return
    try:
        file_field.delete(save=False)
    except Exception as e:
        logger.error(f"Banner file delete error: {e}", exc_info=True)


# ═══════════════════════════════════════════════
#   لیست بنرها
# ═══════════════════════════════════════════════
@role_required('super_admin', 'app_admin', 'content_admin')
@admin_login_required
def ads_list_view(request):
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page_number = request.GET.get('page', 1)

    queryset = AdBanner.objects.select_related('business').order_by('order', '-created_at')
    
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(business__name__icontains=search))
        
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'banners': page_obj.object_list, 
        'status_filter': status_filter,
    }
    return render(request, 'dashboard/ads/list.html', context)


# ═══════════════════════════════════════════════
#   ایجاد بنر
# ═══════════════════════════════════════════════
@role_required('super_admin', 'app_admin', 'content_admin')
@admin_login_required
def ads_create_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        business_id = request.POST.get('business')
        custom_url = request.POST.get('custom_url', '').strip()
        badge = request.POST.get('badge', '').strip()
        order = request.POST.get('order', '0').strip()
        
        # پردازش تاریخ و ساعت
        starts_at_raw = request.POST.get('starts_at')
        expires_at_raw = request.POST.get('expires_at')
        image = request.FILES.get('image')

        if not title:
            messages.error(request, 'عنوان بنر الزامی است.')
            return redirect(reverse('dashboard:ads_create'))

        try:
            if image:
                validate_banner_image(image)
        except ValueError as ve:
            messages.error(request, str(ve))
            return redirect(reverse('dashboard:ads_create'))

        try:
            banner = AdBanner(
                title=title,
                description=description,
                custom_url=custom_url,
                badge=badge,
                order=int(order) if order else 0,
                starts_at=parse_datetime(starts_at_raw) if starts_at_raw else None,
                expires_at=parse_datetime(expires_at_raw) if expires_at_raw else None,
            )
            if business_id:
                banner.business_id = business_id
            if image:
                banner.image = image
                
            banner.full_clean() # ✅ فعال‌سازی متد clean() مدل برای بررسی business یا custom_url
            banner.save()
            messages.success(request, 'بنر تبلیغاتی با موفقیت ایجاد شد.')
            return redirect(reverse('dashboard:ads_list'))
            
        except ValidationError as ve:
            for msg in ve.messages:
                messages.error(request, msg)
        except Exception as e:
            logger.error(f"Ads create error: {e}", exc_info=True)
            messages.error(request, 'خطای غیرمنتظره در ایجاد بنر.')

    businesses = Business.objects.filter(is_active=True, status='approved').order_by('name')
    context = {'businesses': businesses}
    return render(request, 'dashboard/ads/create.html', context)


# ═══════════════════════════════════════════════
#   ویرایش بنر
# ═══════════════════════════════════════════════
@role_required('super_admin', 'app_admin', 'content_admin')
@admin_login_required
def ads_edit_view(request, banner_id):
    banner = get_object_or_404(AdBanner, id=banner_id)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        business_id = request.POST.get('business')
        custom_url = request.POST.get('custom_url', '').strip()
        badge = request.POST.get('badge', '').strip()
        order = request.POST.get('order', '0').strip()
        starts_at_raw = request.POST.get('starts_at')
        expires_at_raw = request.POST.get('expires_at')
        new_image = request.FILES.get('image')
        
        if not title:
            messages.error(request, 'عنوان بنر الزامی است.')
            return redirect(reverse('dashboard:ads_edit', kwargs={'banner_id': banner_id}))

        try:
            if new_image:
                validate_banner_image(new_image)
        except ValueError as ve:
            messages.error(request, str(ve))
            return redirect(reverse('dashboard:ads_edit', kwargs={'banner_id': banner_id}))

        try:
            banner.title = title
            banner.description = description
            banner.custom_url = custom_url
            banner.badge = badge
            banner.order = int(order) if order else 0
            banner.starts_at = parse_datetime(starts_at_raw) if starts_at_raw else None
            banner.expires_at = parse_datetime(expires_at_raw) if expires_at_raw else None
            
            if business_id:
                banner.business_id = business_id
            else:
                banner.business = None
                
            if new_image:
                safe_delete_file(banner.image)
                banner.image = new_image
                
            banner.full_clean()
            banner.save()
            messages.success(request, 'بنر تبلیغاتی با موفقیت ویرایش شد.')
            return redirect(reverse('dashboard:ads_list'))
            
        except ValidationError as ve:
            for msg in ve.messages:
                messages.error(request, msg)
        except Exception as e:
            logger.error(f"Ads edit error: {e}", exc_info=True)
            messages.error(request, 'خطای غیرمنتظره در ویرایش بنر.')

    businesses = Business.objects.filter(is_active=True, status='approved').order_by('name')
    context = {
        'banner': banner, 
        'businesses': businesses,
        # فرمت استاندارد برای input datetime-local در HTML
        'starts_at_val': banner.starts_at.strftime('%Y-%m-%dT%H:%M') if banner.starts_at else '',
        'expires_at_val': banner.expires_at.strftime('%Y-%m-%dT%H:%M') if banner.expires_at else '',
    }
    return render(request, 'dashboard/ads/edit.html', context)


# ═══════════════════════════════════════════════
#   حذف و تغییر وضعیت
# ═══════════════════════════════════════════════
@role_required('super_admin', 'app_admin', 'content_admin')
@admin_login_required
def ads_delete_view(request, banner_id):
    banner = get_object_or_404(AdBanner, id=banner_id)
    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:ads_list'))
        try:
            safe_delete_file(banner.image)
            banner.delete()
            messages.success(request, f'بنر "{banner.title}" حذف شد.')
        except Exception as e:
            logger.error(f"Ads delete error: {e}")
            messages.error(request, 'خطا در حذف بنر.')
    return redirect(reverse('dashboard:ads_list'))

@role_required('super_admin', 'app_admin', 'content_admin')
@admin_login_required
def ads_toggle_active_view(request, banner_id):
    banner = get_object_or_404(AdBanner, id=banner_id)
    if request.method == 'POST':
        banner.is_active = not banner.is_active
        banner.save(update_fields=['is_active', 'updated_at'])
        status_text = 'فعال' if banner.is_active else 'غیرفعال'
        messages.success(request, f'بنر "{banner.title}" {status_text} شد.')
    return redirect(reverse('dashboard:ads_list'))