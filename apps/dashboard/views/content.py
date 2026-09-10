# apps/dashboard/views/content.py
"""
مدیریت محتوا — اکسپلور، نمونه‌کارها، آگهی‌ها، لیست قیمت
✅ فاز ۳: رفع ۶ باگ
- ۳.۴.۱: اعتبارسنجی نوع و حجم فایل آپلودی
- ۳.۴.۲: هندل خطای حذف فایل فیزیکی
- ۳.۴.۳: حذف فایل قبلی هنگام جایگزینی کاور
- ۳.۴.۴: اعتبارسنجی فرمت contact_phone
- ۳.۴.۵: اعتبارسنجی جمع درصدها
- ۳.۴.۶: اعتبارسنجی min_value <= max_value
"""
import logging
import os
import jdatetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.db import DatabaseError
from apps.explore.models import ExplorePost, PostImage
from apps.portfolios.models import Portfolio, PortfolioImage
from apps.ads.models import ModelRequest, LineRental
from apps.services.models import PriceList, PriceListNote
from apps.categories.models import ServiceCategory, SubService
from apps.businesses.models import Business
from apps.dashboard.decorators import admin_login_required, role_required

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۴.۱: اعتبارسنجی فایل‌های آپلودی
# ═══════════════════════════════════════════════
ALLOWED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.gif',
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # ۵ مگابایت
MAX_UPLOAD_IMAGES = 5


def validate_uploaded_image(file_obj):
    """اعتبارسنجی فایل تصویر آپلودی"""
    if file_obj is None:
        return None

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            f'فرمت فایل "{ext}" مجاز نیست. '
            f'فرمت‌های مجاز: '
            + '، '.join(ALLOWED_IMAGE_EXTENSIONS)
        )

    if file_obj.size > MAX_IMAGE_SIZE:
        raise ValueError(
            'حجم تصویر نباید بیشتر از ۵ مگابایت باشد.'
        )

    return file_obj


def safe_delete_file(file_field):
    """حذف امن فایل از دیسک با هندل خطا"""
    if not file_field:
        return
    try:
        file_field.delete(save=False)
    except FileNotFoundError:
        logger.warning(
            f"File not found during delete: {file_field.name}"
        )
    except Exception as e:
        logger.error(
            f"File delete error: {e}",
            exc_info=True,
        )


# ═══════════════════════════════════════════════
#   داشبورد محتوا (بدون تغییر)
# ═══════════════════════════════════════════════
@admin_login_required
def content_index_view(request):
    """داشبورد اصلی مدیریت محتوا با آمار"""
    try:
        explore_stats = ExplorePost.objects.aggregate(
            total=Count('id'),
            pinned=Count('id', filter=Q(is_pinned=True)),
            business=Count('id', filter=Q(source='business')),
            magazine=Count('id', filter=Q(source='magazine')),
        )
        portfolio_stats = Portfolio.objects.aggregate(total=Count('id'))
        model_request_stats = ModelRequest.objects.aggregate(
            total=Count('id'),
            urgent=Count('id', filter=Q(is_urgent=True)),
        )
        line_rental_stats = LineRental.objects.aggregate(total=Count('id'))
        price_list_stats = PriceList.objects.aggregate(
            total=Count('id'),
            published=Count('id', filter=Q(is_published=True)),
        )
    except DatabaseError as e:
        logger.error(f"Content index DB error: {e}")
        messages.error(request, 'خطا در دریافت آمار محتوا.')
        explore_stats = {'total': 0, 'pinned': 0, 'business': 0, 'magazine': 0}
        portfolio_stats = {'total': 0}
        model_request_stats = {'total': 0, 'urgent': 0}
        line_rental_stats = {'total': 0}
        price_list_stats = {'total': 0, 'published': 0}

    recent_posts = ExplorePost.objects.select_related(
        'business'
    ).order_by('-created_at')[:5]
    recent_portfolios = Portfolio.objects.select_related(
        'business', 'category'
    ).order_by('-created_at')[:5]

    context = {
        'explore_stats': explore_stats,
        'portfolio_stats': portfolio_stats,
        'model_request_stats': model_request_stats,
        'line_rental_stats': line_rental_stats,
        'price_list_stats': price_list_stats,
        'recent_posts': recent_posts,
        'recent_portfolios': recent_portfolios,
    }
    return render(request, 'dashboard/content/index.html', context)


# ═══════════════════════════════════════════════
#   اکسپلور — لیست (بدون تغییر)
# ═══════════════════════════════════════════════
@admin_login_required
def explore_list_view(request):
    """لیست پست‌های اکسپلور"""
    search = request.GET.get('search', '').strip()
    source_filter = request.GET.get('source', 'all')
    pinned_filter = request.GET.get('pinned', 'all')
    page_number = request.GET.get('page', 1)

    queryset = ExplorePost.objects.filter(is_active=True).select_related(
        'business', 'main_category'
    ).prefetch_related('images').order_by('-is_pinned', '-created_at')

    if search:
        queryset = queryset.filter(
            Q(caption__icontains=search) |
            Q(business__name__icontains=search)
        )

    if source_filter == 'business':
        queryset = queryset.filter(source='business')
    elif source_filter == 'magazine':
        queryset = queryset.filter(source='magazine')

    if pinned_filter == 'pinned':
        queryset = queryset.filter(is_pinned=True)
    elif pinned_filter == 'unpinned':
        queryset = queryset.filter(is_pinned=False)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': ExplorePost.objects.count(),
            'pinned': ExplorePost.objects.filter(is_pinned=True).count(),
            'business': ExplorePost.objects.filter(source='business').count(),
            'magazine': ExplorePost.objects.filter(source='magazine').count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'pinned': 0, 'business': 0, 'magazine': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'source_filter': source_filter,
        'pinned_filter': pinned_filter,
        'stats': stats,
    }
    return render(request, 'dashboard/content/explore_list.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۴.۱: ایجاد پست اکسپلور با اعتبارسنجی فایل
# ═══════════════════════════════════════════════
@role_required('content_admin', 'super_admin')
@admin_login_required
def explore_create_view(request):
    """ایجاد پست اکسپلور مجله توسط ادمین محتوا"""
    if request.method == 'POST':
        caption = request.POST.get('caption', '').strip()
        business_id = request.POST.get('business')
        category_id = request.POST.get('main_category', '')
        sub_category_id = request.POST.get('sub_category', '')

        if not caption or len(caption) < 10:
            messages.error(request, 'کپشن باید حداقل ۱۰ کاراکتر باشد.')
            return redirect(reverse('dashboard:explore_create'))

        if not business_id:
            messages.error(request, 'انتخاب کسب‌وکار الزامی است.')
            return redirect(reverse('dashboard:explore_create'))

        try:
            business = Business.objects.get(
                id=business_id, is_active=True, status='approved'
            )
        except Business.DoesNotExist:
            messages.error(request, 'کسب‌وکار معتبر یافت نشد.')
            return redirect(reverse('dashboard:explore_create'))

        # ✅ FIX ۳.۴.۱: اعتبارسنجی تصاویر قبل از ایجاد پست
        images = request.FILES.getlist('images')
        validated_images = []
        for img in images[:MAX_UPLOAD_IMAGES]:
            try:
                validated_images.append(validate_uploaded_image(img))
            except ValueError as ve:
                messages.error(request, str(ve))
                return redirect(reverse('dashboard:explore_create'))

        try:
            post = ExplorePost.objects.create(
                business=business,
                source=ExplorePost.Source.MAGAZINE,
                caption=caption,
                main_category_id=category_id or None,
                sub_category_id=sub_category_id or None,
            )

            for i, img in enumerate(validated_images):
                PostImage.objects.create(
                    post=post, image=img, sort_order=i
                )

            messages.success(request, 'پست مجله با موفقیت ایجاد شد.')
            logger.info(
                f"Magazine post created by "
                f"{request.session.get('dashboard_admin_phone')}"
            )
            return redirect(reverse('dashboard:explore_list'))

        except Exception as e:
            logger.error(f"Explore create error: {e}", exc_info=True)
            messages.error(request, 'خطا در ایجاد پست.')

    businesses = Business.objects.filter(
        is_active=True, status='approved'
    ).order_by('name')
    categories = ServiceCategory.objects.filter(is_active=True)
    sub_services = SubService.objects.filter(is_active=True).select_related('category')

    context = {
        'businesses': businesses,
        'categories': categories,
        'sub_services': sub_services,
    }
    return render(request, 'dashboard/content/explore_create.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۴.۲: ویرایش پست اکسپلور با هندل خطای فایل
# ═══════════════════════════════════════════════
@role_required('content_admin', 'super_admin')
@admin_login_required
def explore_edit_view(request, post_id):
    """ویرایش پست اکسپلور"""
    post = get_object_or_404(ExplorePost, id=post_id)

    if request.method == 'POST':
        caption = request.POST.get('caption', '').strip()
        category_id = request.POST.get('main_category', '')
        sub_category_id = request.POST.get('sub_category', '')

        if not caption or len(caption) < 10:
            messages.error(request, 'کپشن باید حداقل ۱۰ کاراکتر باشد.')
            return redirect(
                reverse('dashboard:explore_edit', kwargs={'post_id': post_id})
            )

        try:
            post.caption = caption
            post.main_category_id = category_id or None
            post.sub_category_id = sub_category_id or None
            post.save()

            # حذف تصاویر انتخاب‌شده
            delete_ids = request.POST.getlist('delete_images')
            if delete_ids:
                for img_id in delete_ids:
                    try:
                        img = PostImage.objects.get(id=int(img_id), post=post)
                        # ✅ FIX ۳.۴.۲: حذف امن فایل با هندل خطا
                        safe_delete_file(img.image)
                        img.delete()
                    except (PostImage.DoesNotExist, ValueError):
                        pass
                    except Exception as e:
                        logger.error(
                            f"Explore image delete error: {e}",
                            exc_info=True,
                        )

            # افزودن تصاویر جدید
            new_images = request.FILES.getlist('images')
            current_count = post.images.count()
            for i, img in enumerate(new_images):
                if current_count + i >= MAX_UPLOAD_IMAGES:
                    messages.warning(
                        request,
                        f'حداکثر {MAX_UPLOAD_IMAGES} تصویر مجاز است. '
                        f'تصاویر اضافی نادیده گرفته شدند.'
                    )
                    break
                try:
                    validate_uploaded_image(img)
                except ValueError as ve:
                    messages.warning(request, str(ve))
                    continue
                PostImage.objects.create(
                    post=post, image=img,
                    sort_order=current_count + i,
                )

            messages.success(request, 'پست با موفقیت ویرایش شد.')
            return redirect(reverse('dashboard:explore_list'))

        except Exception as e:
            logger.error(f"Explore edit error: {e}", exc_info=True)
            messages.error(request, 'خطا در ویرایش پست.')

    categories = ServiceCategory.objects.filter(is_active=True)
    sub_services = SubService.objects.filter(is_active=True).select_related('category')

    context = {
        'post': post,
        'categories': categories,
        'sub_services': sub_services,
    }
    return render(request, 'dashboard/content/explore_edit.html', context)


# ═══════════════════════════════════════════════
#   اکسپلور — پین/حذف (بدون تغییر)
# ═══════════════════════════════════════════════
@admin_login_required
def explore_toggle_pin_view(request, post_id):
    """پین/آنپین پست اکسپلور"""
    post = get_object_or_404(ExplorePost, id=post_id)

    if request.method == 'POST':
        try:
            post.is_pinned = not post.is_pinned
            post.save(update_fields=['is_pinned'])
            status_text = 'پین شد' if post.is_pinned else 'از پین خارج شد'
            messages.success(request, f'پست {status_text}.')
        except Exception as e:
            logger.error(f"Pin toggle error: {e}")
            messages.error(request, 'خطا در تغییر وضعیت پست.')

    return redirect(reverse('dashboard:explore_list'))


@admin_login_required
def explore_delete_view(request, post_id):
    """حذف پست اکسپلور"""
    post = get_object_or_404(ExplorePost, id=post_id)

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:explore_list'))

        try:
            caption_preview = post.caption[:30]
            for image in post.images.all():
                safe_delete_file(image.image)
            post.delete()
            messages.success(request, f'پست "{caption_preview}..." حذف شد.')
        except Exception as e:
            logger.error(f"Explore delete error: {e}")
            messages.error(request, 'خطا در حذف پست.')

    return redirect(reverse('dashboard:explore_list'))


# ═══════════════════════════════════════════════
#   نمونه‌کارها — لیست (بدون تغییر)
# ═══════════════════════════════════════════════
@admin_login_required
def portfolios_list_view(request):
    """لیست نمونه‌کارها"""
    search = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)

    queryset = Portfolio.objects.select_related(
        'business', 'category', 'sub_service'
    ).prefetch_related('images').order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(business__name__icontains=search) |
            Q(category__name__icontains=search)
        )

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {'total': Portfolio.objects.count()}
    except DatabaseError:
        stats = {'total': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'stats': stats,
    }
    return render(request, 'dashboard/content/portfolios_list.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۴.۳: ویرایش نمونه‌کار با حذف فایل قبلی
# ═══════════════════════════════════════════════
@role_required('content_admin', 'super_admin')
@admin_login_required
def portfolio_edit_view(request, portfolio_id):
    """ویرایش نمونه‌کار"""
    portfolio = get_object_or_404(Portfolio, id=portfolio_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category', '')
        sub_service_id = request.POST.get('sub_service', '')

        if not title or len(title) < 3:
            messages.error(request, 'عنوان باید حداقل ۳ کاراکتر باشد.')
            return redirect(
                reverse('dashboard:portfolio_edit',
                        kwargs={'portfolio_id': portfolio_id})
            )

        try:
            portfolio.title = title
            portfolio.description = description
            if category_id:
                portfolio.category_id = int(category_id)
            if sub_service_id:
                portfolio.sub_service_id = int(sub_service_id)
            portfolio.save()

            # حذف تصاویر انتخاب‌شده
            delete_ids = request.POST.getlist('delete_images')
            if delete_ids:
                for img_id in delete_ids:
                    try:
                        img = PortfolioImage.objects.get(
                            id=int(img_id), portfolio=portfolio
                        )
                        safe_delete_file(img.image)
                        img.delete()
                    except (PortfolioImage.DoesNotExist, ValueError):
                        pass

            # افزودن تصاویر جدید
            new_images = request.FILES.getlist('images')
            current_count = portfolio.images.count()
            for i, img in enumerate(new_images):
                if current_count + i >= 3:
                    messages.warning(
                        request,
                        'حداکثر ۳ تصویر در گالری مجاز است. '
                        'تصاویر اضافی نادیده گرفته شدند.'
                    )
                    break
                try:
                    validate_uploaded_image(img)
                except ValueError as ve:
                    messages.warning(request, str(ve))
                    continue
                PortfolioImage.objects.create(
                    portfolio=portfolio, image=img,
                    sort_order=current_count + i,
                )

            # ✅ FIX ۳.۴.۳: بروزرسانی کاور با حذف فایل قبلی
            new_cover = request.FILES.get('cover_image')
            if new_cover:
                try:
                    validate_uploaded_image(new_cover)
                except ValueError as ve:
                    messages.warning(request, str(ve))
                else:
                    safe_delete_file(portfolio.cover_image)
                    portfolio.cover_image = new_cover
                    portfolio.save(update_fields=['cover_image'])

            messages.success(request, 'نمونه‌کار با موفقیت ویرایش شد.')
            return redirect(reverse('dashboard:portfolios_list'))

        except Exception as e:
            logger.error(f"Portfolio edit error: {e}", exc_info=True)
            messages.error(request, 'خطا در ویرایش نمونه‌کار.')

    categories = ServiceCategory.objects.filter(is_active=True)
    sub_services = SubService.objects.filter(is_active=True)

    context = {
        'portfolio': portfolio,
        'categories': categories,
        'sub_services': sub_services,
    }
    return render(request, 'dashboard/content/portfolio_edit.html', context)


@admin_login_required
def portfolio_delete_view(request, portfolio_id):
    """حذف نمونه‌کار"""
    portfolio = get_object_or_404(Portfolio, id=portfolio_id)

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:portfolios_list'))

        try:
            title = portfolio.title
            safe_delete_file(portfolio.cover_image)
            for image in portfolio.images.all():
                safe_delete_file(image.image)
            portfolio.delete()
            messages.success(request, f'نمونه‌کار "{title}" حذف شد.')
        except Exception as e:
            logger.error(f"Portfolio delete error: {e}")
            messages.error(request, 'خطا در حذف نمونه‌کار.')

    return redirect(reverse('dashboard:portfolios_list'))


# ═══════════════════════════════════════════════
#   درخواست مدل — لیست (بدون تغییر)
# ═══════════════════════════════════════════════
@admin_login_required
def model_requests_list_view(request):
    """لیست درخواست‌های مدل"""
    search = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)

    queryset = ModelRequest.objects.select_related(
        'business', 'service'
    ).order_by('-is_urgent', '-created_at')

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(business__name__icontains=search)
        )

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': ModelRequest.objects.count(),
            'urgent': ModelRequest.objects.filter(is_urgent=True).count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'urgent': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'stats': stats,
    }
    return render(request, 'dashboard/content/model_requests_list.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۴.۴: ویرایش درخواست مدل با اعتبارسنجی تلفن
# ═══════════════════════════════════════════════
@role_required('content_admin', 'super_admin')
@admin_login_required
def model_request_edit_view(request, request_id):
    """ویرایش درخواست مدل"""
    model_request = get_object_or_404(ModelRequest, id=request_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        cost_type = request.POST.get('cost_type', model_request.cost_type)
        discount_str = request.POST.get('discount', '0').strip()
        is_urgent = request.POST.get('is_urgent') == 'on'
        contact_phone = request.POST.get('contact_phone', '').strip()

        if not title or len(title) < 3:
            messages.error(request, 'عنوان باید حداقل ۳ کاراکتر باشد.')
            return redirect(
                reverse('dashboard:model_request_edit',
                        kwargs={'request_id': request_id})
            )

        if cost_type not in dict(ModelRequest.CostType.choices):
            messages.error(request, 'نوع هزینه نامعتبر است.')
            return redirect(
                reverse('dashboard:model_request_edit',
                        kwargs={'request_id': request_id})
            )

        # ✅ FIX ۳.۴.۴: اعتبارسنجی فرمت شماره تماس
        if contact_phone:
            try:
                from apps.core.validators import validate_iranian_phone
                contact_phone = validate_iranian_phone(contact_phone)
            except Exception:
                messages.error(
                    request,
                    'شماره تماس باید فرمت معتبر ایرانی باشد '
                    '(مثلاً ۰۹۱۲۳۴۵۶۷۸۹).'
                )
                return redirect(
                    reverse('dashboard:model_request_edit',
                            kwargs={'request_id': request_id})
                )

        try:
            discount = int(discount_str)
            if not (0 <= discount <= 100):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'درصد تخفیف باید بین ۰ تا ۱۰۰ باشد.')
            return redirect(
                reverse('dashboard:model_request_edit',
                        kwargs={'request_id': request_id})
            )

        try:
            model_request.title = title
            model_request.description = description
            model_request.cost_type = cost_type
            model_request.discount = discount
            model_request.is_urgent = is_urgent
            if contact_phone:
                model_request.contact_phone = contact_phone

            new_image = request.FILES.get('service_image')
            if new_image:
                try:
                    validate_uploaded_image(new_image)
                except ValueError as ve:
                    messages.warning(request, str(ve))
                else:
                    safe_delete_file(model_request.service_image)
                    model_request.service_image = new_image

            model_request.save()
            messages.success(request, 'درخواست مدل ویرایش شد.')
            return redirect(reverse('dashboard:model_requests_list'))

        except Exception as e:
            logger.error(f"Model request edit error: {e}", exc_info=True)
            messages.error(request, 'خطا در ویرایش درخواست مدل.')

    context = {
        'model_request': model_request,
        'cost_type_choices': ModelRequest.CostType.choices,
    }
    return render(request, 'dashboard/content/model_request_edit.html', context)


@admin_login_required
def model_request_delete_view(request, request_id):
    """حذف درخواست مدل"""
    model_request = get_object_or_404(ModelRequest, id=request_id)

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:model_requests_list'))

        try:
            title = model_request.title
            safe_delete_file(model_request.service_image)
            model_request.delete()
            messages.success(request, f'درخواست مدل "{title}" حذف شد.')
        except Exception as e:
            logger.error(f"Model request delete error: {e}")
            messages.error(request, 'خطا در حذف درخواست مدل.')

    return redirect(reverse('dashboard:model_requests_list'))


# ═══════════════════════════════════════════════
#   اجاره لاین — لیست (بدون تغییر)
# ═══════════════════════════════════════════════
@admin_login_required
def line_rentals_list_view(request):
    """لیست آگهی‌های اجاره لاین"""
    search = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)

    queryset = LineRental.objects.select_related(
        'business', 'service_category'
    ).order_by('-created_at')

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(business__name__icontains=search)
        )

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {'total': LineRental.objects.count()}
    except DatabaseError:
        stats = {'total': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'stats': stats,
    }
    return render(request, 'dashboard/content/line_rentals_list.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۴.۵: ویرایش اجاره لاین با اعتبارسنجی درصدها
# ═══════════════════════════════════════════════
@role_required('content_admin', 'super_admin')
@admin_login_required
def line_rental_edit_view(request, rental_id):
    """ویرایش آگهی اجاره لاین"""
    line_rental = get_object_or_404(LineRental, id=rental_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        collab_type = request.POST.get('collab_type', line_rental.collab_type)
        percent_salon = request.POST.get('percent_salon', '').strip()
        percent_partner = request.POST.get('percent_partner', '').strip()
        fixed_amount = request.POST.get('fixed_amount', '').strip()
        fixed_deposit = request.POST.get('fixed_deposit', '').strip()
        hourly_rate = request.POST.get('hourly_rate', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()

        if not title or len(title) < 3:
            messages.error(request, 'عنوان باید حداقل ۳ کاراکتر باشد.')
            return redirect(
                reverse('dashboard:line_rental_edit',
                        kwargs={'rental_id': rental_id})
            )

        if collab_type not in dict(LineRental.CollabType.choices):
            messages.error(request, 'نوع همکاری نامعتبر است.')
            return redirect(
                reverse('dashboard:line_rental_edit',
                        kwargs={'rental_id': rental_id})
            )

        # ✅ FIX ۳.۴.۵: اعتبارسنجی جمع درصدها برای نوع درصدی
        if collab_type == LineRental.CollabType.PERCENT:
            try:
                salon_pct = int(percent_salon) if percent_salon else 0
                partner_pct = int(percent_partner) if percent_partner else 0
                if salon_pct + partner_pct != 100:
                    messages.error(
                        request,
                        'مجموع سهم سالن و همکار باید دقیقاً ۱۰۰٪ باشد.'
                    )
                    return redirect(
                        reverse('dashboard:line_rental_edit',
                                kwargs={'rental_id': rental_id})
                    )
            except (ValueError, TypeError):
                messages.error(request, 'درصدها باید عدد صحیح باشند.')
                return redirect(
                    reverse('dashboard:line_rental_edit',
                            kwargs={'rental_id': rental_id})
                )

        # ✅ FIX ۳.۴.۴: اعتبارسنجی شماره تماس
        if contact_phone:
            try:
                from apps.core.validators import validate_iranian_phone
                contact_phone = validate_iranian_phone(contact_phone)
            except Exception:
                messages.error(request, 'شماره تماس نامعتبر است.')
                return redirect(
                    reverse('dashboard:line_rental_edit',
                            kwargs={'rental_id': rental_id})
                )

        try:
            line_rental.title = title
            line_rental.description = description
            line_rental.collab_type = collab_type
            line_rental.percent_salon = int(percent_salon) if percent_salon else None
            line_rental.percent_partner = int(percent_partner) if percent_partner else None
            line_rental.fixed_amount = int(fixed_amount) if fixed_amount else None
            line_rental.fixed_deposit = int(fixed_deposit) if fixed_deposit else None
            line_rental.hourly_rate = int(hourly_rate) if hourly_rate else None
            if contact_phone:
                line_rental.contact_phone = contact_phone

            new_image = request.FILES.get('line_image')
            if new_image:
                try:
                    validate_uploaded_image(new_image)
                except ValueError as ve:
                    messages.warning(request, str(ve))
                else:
                    safe_delete_file(line_rental.line_image)
                    line_rental.line_image = new_image

            line_rental.save()
            messages.success(request, 'آگهی لاین ویرایش شد.')
            return redirect(reverse('dashboard:line_rentals_list'))

        except (ValueError, TypeError):
            messages.error(request, 'مقادیر عددی نامعتبر هستند.')
        except Exception as e:
            logger.error(f"Line rental edit error: {e}", exc_info=True)
            messages.error(request, 'خطا در ویرایش آگهی.')

    context = {
        'line_rental': line_rental,
        'collab_choices': LineRental.CollabType.choices,
    }
    return render(request, 'dashboard/content/line_rental_edit.html', context)


@admin_login_required
def line_rental_delete_view(request, rental_id):
    """حذف آگهی اجاره لاین"""
    line_rental = get_object_or_404(LineRental, id=rental_id)

    if request.method == 'POST':
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:line_rentals_list'))

        try:
            title = line_rental.title
            safe_delete_file(line_rental.line_image)
            line_rental.delete()
            messages.success(request, f'آگهی لاین "{title}" حذف شد.')
        except Exception as e:
            logger.error(f"Line rental delete error: {e}")
            messages.error(request, 'خطا در حذف آگهی.')

    return redirect(reverse('dashboard:line_rentals_list'))


# ═══════════════════════════════════════════════
#   لیست قیمت — لیست (بدون تغییر)
# ═══════════════════════════════════════════════
@admin_login_required
def price_lists_view(request):
    """لیست لیست‌های قیمت"""
    search = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)

    queryset = PriceList.objects.select_related(
        'business'
    ).prefetch_related('notes').order_by('-created_at')

    if search:
        queryset = queryset.filter(business__name__icontains=search)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    try:
        stats = {
            'total': PriceList.objects.count(),
            'published': PriceList.objects.filter(is_published=True).count(),
        }
    except DatabaseError:
        stats = {'total': 0, 'published': 0}

    context = {
        'page_obj': page_obj,
        'search': search,
        'stats': stats,
    }
    return render(request, 'dashboard/content/price_lists.html', context)


# ═══════════════════════════════════════════════
#   ✅ FIX ۳.۴.۶: ویرایش لیست قیمت با اعتبارسنجی مقادیر
# ═══════════════════════════════════════════════
@role_required('content_admin', 'super_admin')
@admin_login_required
def price_list_edit_view(request, price_list_id):
    """ویرایش لیست قیمت"""
    price_list = get_object_or_404(
        PriceList.objects.prefetch_related('notes'),
        id=price_list_id,
    )

    if request.method == 'POST':
        theme = request.POST.get('theme', price_list.theme)
        is_published = request.POST.get('is_published') == 'on'

        if theme not in dict(PriceList.ThemeChoices.choices):
            messages.error(request, 'تم نامعتبر است.')
            return redirect(
                reverse('dashboard:price_list_edit',
                        kwargs={'price_list_id': price_list_id})
            )

        try:
            price_list.theme = theme
            price_list.is_published = is_published
            price_list.save()

            # حذف notes انتخاب‌شده
            delete_ids = request.POST.getlist('delete_notes')
            if delete_ids:
                for note_id in delete_ids:
                    try:
                        PriceListNote.objects.filter(
                            id=int(note_id), price_list=price_list
                        ).delete()
                    except (ValueError, TypeError):
                        pass

            # افزودن note جدید
            new_label = request.POST.get('new_note_label', '').strip()
            new_min = request.POST.get('new_note_min', '0').strip()
            new_max = request.POST.get('new_note_max', '0').strip()

            if new_label:
                try:
                    min_val = int(new_min)
                    max_val = int(new_max)

                    # ✅ FIX ۳.۴.۶: اعتبارسنجی min <= max
                    if min_val > max_val:
                        messages.error(
                            request,
                            'مقدار حداقل نمی‌تواند بیشتر از حداکثر باشد.'
                        )
                        return redirect(
                            reverse('dashboard:price_list_edit',
                                    kwargs={'price_list_id': price_list_id})
                        )

                    if min_val < 0 or max_val < 0:
                        messages.error(
                            request,
                            'مقادیر حداقل و حداکثر نمی‌توانند منفی باشند.'
                        )
                        return redirect(
                            reverse('dashboard:price_list_edit',
                                    kwargs={'price_list_id': price_list_id})
                        )

                    PriceListNote.objects.create(
                        price_list=price_list,
                        label=new_label,
                        min_value=min_val,
                        max_value=max_val,
                    )
                except (ValueError, TypeError):
                    messages.warning(request, 'مقادیر یادداشت جدید نامعتبر بودند.')

            messages.success(request, 'لیست قیمت ویرایش شد.')
            return redirect(reverse('dashboard:price_lists'))

        except Exception as e:
            logger.error(f"Price list edit error: {e}", exc_info=True)
            messages.error(request, 'خطا در ویرایش لیست قیمت.')

    context = {
        'price_list': price_list,
        'theme_choices': PriceList.ThemeChoices.choices,
    }
    return render(request, 'dashboard/content/price_list_edit.html', context)