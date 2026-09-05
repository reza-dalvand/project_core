"""
مدیریت محتوا — اکسپلور، نمونه‌کارها، آگهی‌ها، لیست قیمت
✅ فاز ۳: مکانیزم تأیید حذف + هندل خطا
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.db import DatabaseError
from apps.explore.models import ExplorePost
from apps.portfolios.models import Portfolio
from apps.ads.models import ModelRequest, LineRental
from apps.services.models import PriceList
from apps.dashboard.decorators import admin_login_required

logger = logging.getLogger(__name__)


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

    # لیست‌های اخیر
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
#   اکسپلور
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


@admin_login_required
def explore_toggle_pin_view(request, post_id):
    """پین/آنپین پست اکسپلور"""
    post = get_object_or_404(ExplorePost, id=post_id)

    if request.method == 'POST':
        try:
            post.is_pinned = not post.is_pinned
            post.save(update_fields=['is_pinned'])

            status_text = 'پین شد' if post.is_pinned else 'از پین خارج شد'
            messages.success(request, f'پست "{post.caption[:30]}..." {status_text}.')
            logger.info(f"Explore post {post_id} {'pinned' if post.is_pinned else 'unpinned'}")

        except DatabaseError as e:
            logger.error(f"Explore pin toggle DB error: {e}")
            messages.error(request, 'خطا در تغییر وضعیت پست.')
        except Exception as e:
            logger.error(f"Explore pin toggle unexpected error: {e}")
            messages.error(request, 'خطای غیرمنتظره در تغییر وضعیت پست.')

    return redirect(reverse('dashboard:explore_list'))


@admin_login_required
def explore_delete_view(request, post_id):
    """حذف پست اکسپلور"""
    post = get_object_or_404(ExplorePost, id=post_id)

    if request.method == 'POST':
        # ✅ فاز ۳: مکانیزم تأیید سمت سرور
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:explore_list'))

        try:
            caption_preview = post.caption[:30]

            # حذف تصاویر از دیسک
            for image in post.images.all():
                if image.image:
                    try:
                        image.image.delete(save=False)
                    except Exception:
                        pass

            post.delete()

            messages.success(request, f'پست "{caption_preview}..." حذف شد.')
            logger.info(f"Explore post {post_id} deleted")

        except Exception as e:
            logger.error(f"Explore delete error: {e}")
            messages.error(request, 'خطا در حذف پست. لطفاً دوباره تلاش کنید.')

    return redirect(reverse('dashboard:explore_list'))


# ═══════════════════════════════════════════════
#   نمونه‌کارها
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


@admin_login_required
def portfolio_delete_view(request, portfolio_id):
    """حذف نمونه‌کار"""
    portfolio = get_object_or_404(Portfolio, id=portfolio_id)

    if request.method == 'POST':
        # ✅ فاز ۳: مکانیزم تأیید سمت سرور
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:portfolios_list'))

        try:
            title = portfolio.title

            if portfolio.cover_image:
                try:
                    portfolio.cover_image.delete(save=False)
                except Exception:
                    pass

            for image in portfolio.images.all():
                if image.image:
                    try:
                        image.image.delete(save=False)
                    except Exception:
                        pass

            portfolio.delete()

            messages.success(request, f'نمونه‌کار "{title}" حذف شد.')
            logger.info(f"Portfolio {portfolio_id} deleted")

        except Exception as e:
            logger.error(f"Portfolio delete error: {e}")
            messages.error(request, 'خطا در حذف نمونه‌کار.')

    return redirect(reverse('dashboard:portfolios_list'))


# ═══════════════════════════════════════════════
#   آگهی‌ها
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


@admin_login_required
def model_request_delete_view(request, request_id):
    """حذف درخواست مدل"""
    model_request = get_object_or_404(ModelRequest, id=request_id)

    if request.method == 'POST':
        # ✅ فاز ۳: مکانیزم تأیید سمت سرور
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:model_requests_list'))

        try:
            title = model_request.title
            if model_request.service_image:
                try:
                    model_request.service_image.delete(save=False)
                except Exception:
                    pass

            model_request.delete()
            messages.success(request, f'درخواست مدل "{title}" حذف شد.')
            logger.info(f"Model request {request_id} deleted")

        except Exception as e:
            logger.error(f"Model request delete error: {e}")
            messages.error(request, 'خطا در حذف درخواست مدل.')

    return redirect(reverse('dashboard:model_requests_list'))


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


@admin_login_required
def line_rental_delete_view(request, rental_id):
    """حذف آگهی اجاره لاین"""
    line_rental = get_object_or_404(LineRental, id=rental_id)

    if request.method == 'POST':
        # ✅ فاز ۳: مکانیزم تأیید سمت سرور
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'عملیات حذف تایید نشد.')
            return redirect(reverse('dashboard:line_rentals_list'))

        try:
            title = line_rental.title
            if line_rental.line_image:
                try:
                    line_rental.line_image.delete(save=False)
                except Exception:
                    pass

            line_rental.delete()
            messages.success(request, f'آگهی لاین "{title}" حذف شد.')
            logger.info(f"Line rental {rental_id} deleted")

        except Exception as e:
            logger.error(f"Line rental delete error: {e}")
            messages.error(request, 'خطا در حذف آگهی.')

    return redirect(reverse('dashboard:line_rentals_list'))


# ═══════════════════════════════════════════════
#   لیست قیمت
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
        queryset = queryset.filter(
            Q(business__name__icontains=search)
        )

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