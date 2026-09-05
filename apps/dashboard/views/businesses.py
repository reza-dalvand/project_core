# apps/dashboard/views/businesses.py

"""
مدیریت کسب‌وکارها — لیست، فیلتر، جزئیات، تایید/رد
✅ فاز ۵: رفع N+1 + select_related + only()
"""

import logging
import secrets

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify

from apps.appointments.models import Appointment
from apps.businesses.models import Business, BusinessGallery
from apps.categories.models import BusinessCategory
from apps.dashboard.decorators import admin_login_required, role_required
from apps.dashboard.services.audit_service import DashboardAuditService
from apps.dashboard.services.cache_service import DashboardCacheService
from apps.locations.models import City, Province
from apps.services.models import Service


logger = logging.getLogger(__name__)


@admin_login_required
def businesses_list_view(request):
    """لیست کسب‌وکارها با جستجو و فیلتر"""

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "all")
    page_number = request.GET.get("page", 1)

    # ✅ فاز ۵: رفع N+1 با select_related + only()
    queryset = (
        Business.objects.filter(is_active=True)
        .select_related(
            "owner",
            "category",
            "city",
            "province",
        )
        .only(
            "id",
            "name",
            "status",
            "is_vip",
            "rating",
            "reviews_count",
            "created_at",
            "booking_slug",
            "owner__phone",
            "owner__first_name",
            "owner__last_name",
            "category__name",
            "city__name",
            "province__name",
        )
        .annotate(
            services_count=Count(
                "services",
                filter=Q(services__is_active=True),
            ),
            appointments_count=Count(
                "appointments",
                filter=Q(appointments__is_active=True),
            ),
        )
        .order_by("-created_at")
    )

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(owner__phone__icontains=search)
            | Q(owner__first_name__icontains=search)
            | Q(city__name__icontains=search)
        )

    if status_filter == "pending":
        queryset = queryset.filter(
            status=Business.Status.PENDING
        )
    elif status_filter == "approved":
        queryset = queryset.filter(
            status=Business.Status.APPROVED
        )
    elif status_filter == "rejected":
        queryset = queryset.filter(
            status=Business.Status.REJECTED
        )

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page_number)

    stats = {
        "total": Business.objects.count(),
        "pending": Business.objects.filter(
            status=Business.Status.PENDING
        ).count(),
        "approved": Business.objects.filter(
            status=Business.Status.APPROVED
        ).count(),
        "rejected": Business.objects.filter(
            status=Business.Status.REJECTED
        ).count(),
    }

    context = {
        "page_obj": page_obj,
        "search": search,
        "status_filter": status_filter,
        "stats": stats,
    }

    return render(
        request,
        "dashboard/businesses/list.html",
        context,
    )


# ═══════════════════════════════════════════════
#   جزئیات کسب‌وکار (بهینه‌سازی شده — فاز ۵)
# ═══════════════════════════════════════════════

@admin_login_required
def business_detail_view(request, business_id):
    """جزئیات کسب‌وکار + گالری + خدمات + نوبت‌ها + اطلاعات بانکی"""

    # ✅ فاز ۵: رفع N+1 با select_related + prefetch_related
    business = get_object_or_404(
        Business.objects.select_related(
            "owner",
            "category",
            "city",
            "province",
        ).prefetch_related(
            "services",
            "gallery",
            "reviews",
        ),
        id=business_id,
    )

    # آمار کسب‌وکار
    business_stats = {
        "services_count": business.services.filter(
            is_active=True
        ).count(),
        "appointments_count": business.appointments.count(),
        "reviews_count": business.reviews.count(),
        "avg_rating": business.rating,
        "transactions_count": business.transactions.count(),
        "posts_count": business.posts.count(),
    }

    # خدمات
    services = business.services.all().order_by("-created_at")

    # گالری
    gallery = business.gallery.all().order_by("sort_order")

    # نوبت‌های فعال
    active_appointments = (
        business.appointments.filter(
            status=Appointment.Status.RESERVED,
            is_active=True,
        )
        .select_related(
            "customer",
            "service",
        )
        .order_by("time_slot")[:10]
    )

    # نوبت‌های اخیر
    recent_appointments = (
        business.appointments.select_related(
            "customer",
            "service",
        )
        .order_by("-created_at")[:10]
    )

    # نظرات اخیر
    recent_reviews = (
        business.reviews.select_related("customer")
        .order_by("-created_at")[:5]
    )

    context = {
        "business": business,
        "business_stats": business_stats,
        "services": services,
        "gallery": gallery,
        "active_appointments": active_appointments,
        "recent_appointments": recent_appointments,
        "recent_reviews": recent_reviews,
    }

    return render(
        request,
        "dashboard/businesses/detail.html",
        context,
    )


# ═══════════════════════════════════════════════
#   ایجاد کسب‌وکار (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_create_view(request):
    """ایجاد کسب‌وکار جدید از پنل ادمین"""

    if request.method == "POST":
        from django.contrib.auth import get_user_model

        User = get_user_model()

        name = request.POST.get("name", "").strip()
        owner_phone = request.POST.get("owner_phone", "").strip()
        category_id = request.POST.get("category")
        province_id = request.POST.get("province")
        city_id = request.POST.get("city")
        address = request.POST.get("address", "").strip()
        phone = request.POST.get("phone", "").strip()
        working_hours = request.POST.get(
            "working_hours",
            "",
        ).strip()
        about = request.POST.get("about", "").strip()
        status = request.POST.get("status", "pending")

        # ─── اعتبارسنجی نام ───
        if not name or len(name) < 3:
            messages.error(
                request,
                "نام کسب‌وکار باید حداقل ۳ کاراکتر باشد.",
            )
            return redirect(
                reverse("dashboard:business_create")
            )

        # ─── اعتبارسنجی مالک ───
        if not owner_phone:
            messages.error(
                request,
                "شماره تلفن مالک الزامی است.",
            )
            return redirect(
                reverse("dashboard:business_create")
            )

        try:
            owner = User.objects.get(phone=owner_phone)
        except User.DoesNotExist:
            messages.error(
                request,
                "کاربری با این شماره تلفن یافت نشد.",
            )
            return redirect(
                reverse("dashboard:business_create")
            )

        # ─── بررسی تکراری نبودن ───
        if Business.objects.filter(
            owner=owner,
            is_active=True,
        ).exists():
            messages.error(
                request,
                "این کاربر قبلاً یک کسب‌وکار ثبت کرده است.",
            )
            return redirect(
                reverse("dashboard:business_create")
            )

        # ─── اعتبارسنجی فیلدهای لازم ───
        if not category_id:
            messages.error(
                request,
                "نوع کسب‌وکار الزامی است.",
            )
            return redirect(
                reverse("dashboard:business_create")
            )

        if not province_id:
            messages.error(
                request,
                "استان الزامی است.",
            )
            return redirect(
                reverse("dashboard:business_create")
            )

        if not city_id:
            messages.error(
                request,
                "شهر الزامی است.",
            )
            return redirect(
                reverse("dashboard:business_create")
            )

        if not address or len(address) < 10:
            messages.error(
                request,
                "آدرس باید حداقل ۱۰ کاراکتر باشد.",
            )
            return redirect(
                reverse("dashboard:business_create")
            )

        # ─── ایجاد کسب‌وکار ───
        try:
            business = Business.objects.create(
                owner=owner,
                name=name,
                category_id=category_id,
                province_id=province_id,
                city_id=city_id,
                address=address,
                phone=phone,
                working_hours=working_hours,
                about=about,
                status=status,
            )

            logger.info(
                f"Admin created business: {name} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )

            messages.success(
                request,
                f'کسب‌وکار "{name}" با موفقیت ایجاد شد.',
            )

            return redirect(
                reverse(
                    "dashboard:business_detail",
                    kwargs={"business_id": business.id},
                )
            )

        except Exception as e:
            logger.error(
                f"Business create error: {e}",
                exc_info=True,
            )
            messages.error(
                request,
                "خطا در ایجاد کسب‌وکار.",
            )

    # ─── نمایش فرم ───
    categories = BusinessCategory.objects.filter(
        is_active=True
    )
    provinces = Province.objects.filter(
        is_active=True
    ).order_by("name")
    cities = City.objects.filter(
        is_active=True
    ).select_related("province")

    context = {
        "categories": categories,
        "provinces": provinces,
        "cities": cities,
    }

    return render(
        request,
        "dashboard/businesses/create.html",
        context,
    )


# ═══════════════════════════════════════════════
#   ویرایش کسب‌وکار (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_edit_view(request, business_id):
    """ویرایش اطلاعات کسب‌وکار"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_id = request.POST.get("category")
        province_id = request.POST.get("province")
        city_id = request.POST.get("city")
        address = request.POST.get("address", "").strip()
        phone = request.POST.get("phone", "").strip()
        working_hours = request.POST.get(
            "working_hours",
            "",
        ).strip()
        about = request.POST.get("about", "").strip()

        # ─── اعتبارسنجی ───
        if not name or len(name) < 3:
            messages.error(
                request,
                "نام کسب‌وکار باید حداقل ۳ کاراکتر باشد.",
            )
            return redirect(
                reverse(
                    "dashboard:business_edit",
                    kwargs={"business_id": business_id},
                )
            )

        if not address or len(address) < 10:
            messages.error(
                request,
                "آدرس باید حداقل ۱۰ کاراکتر باشد.",
            )
            return redirect(
                reverse(
                    "dashboard:business_edit",
                    kwargs={"business_id": business_id},
                )
            )

        try:
            business.name = name
            business.address = address
            business.phone = phone
            business.working_hours = working_hours
            business.about = about

            if category_id:
                business.category_id = category_id

            if province_id:
                business.province_id = province_id

            if city_id:
                business.city_id = city_id

            business.save()

            logger.info(
                f"Admin edited business {business.id} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )

            messages.success(
                request,
                f'کسب‌وکار "{name}" با موفقیت بروزرسانی شد.',
            )

            return redirect(
                reverse(
                    "dashboard:business_detail",
                    kwargs={"business_id": business_id},
                )
            )

        except Exception as e:
            logger.error(
                f"Business edit error: {e}",
                exc_info=True,
            )
            messages.error(
                request,
                "خطا در بروزرسانی کسب‌وکار.",
            )

    # ─── نمایش فرم ───
    categories = BusinessCategory.objects.filter(
        is_active=True
    )
    provinces = Province.objects.filter(
        is_active=True
    ).order_by("name")
    cities = City.objects.filter(
        is_active=True
    ).select_related("province")

    context = {
        "business": business,
        "categories": categories,
        "provinces": provinces,
        "cities": cities,
    }

    return render(
        request,
        "dashboard/businesses/edit.html",
        context,
    )


# ═══════════════════════════════════════════════
#   حذف کسب‌وکار (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("super_admin")
@admin_login_required
def business_delete_view(request, business_id):
    """حذف نرم کسب‌وکار — فقط سوپر ادمین"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    if request.method == "POST":
        # ─── تأیید سمت سرور ───
        if request.POST.get("confirm") != "yes":
            messages.error(
                request,
                "عملیات حذف تایید نشد.",
            )
            return redirect(
                reverse(
                    "dashboard:business_detail",
                    kwargs={"business_id": business_id},
                )
            )

        # ─── بررسی نوبت‌های فعال ───
        active_appointments = business.appointments.filter(
            status=Appointment.Status.RESERVED,
            is_active=True,
        ).count()

        if active_appointments > 0:
            messages.error(
                request,
                f"این کسب‌وکار {active_appointments} نوبت فعال دارد. "
                f"ابتدا نوبت‌ها را لغو کنید.",
            )
            return redirect(
                reverse(
                    "dashboard:business_detail",
                    kwargs={"business_id": business_id},
                )
            )

        try:
            name = business.name
            business.is_active = False
            business.save(
                update_fields=["is_active"]
            )

            logger.info(
                f"Admin soft-deleted business {name} "
                f"by {request.session.get('dashboard_admin_phone')}"
            )

            messages.success(
                request,
                f'کسب‌وکار "{name}" حذف شد.',
            )

            return redirect(
                reverse("dashboard:businesses_list")
            )

        except Exception as e:
            logger.error(
                f"Business delete error: {e}",
                exc_info=True,
            )
            messages.error(
                request,
                "خطا در حذف کسب‌وکار.",
            )

    return redirect(
        reverse(
            "dashboard:business_detail",
            kwargs={"business_id": business_id},
        )
    )


# ═══════════════════════════════════════════════
#   ریست لینک رزرو (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_reset_slug_view(request, business_id):
    """ریست اسلاگ رزرو کسب‌وکار"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    if request.method == "POST":
        try:
            base_slug = slugify(
                business.name,
                allow_unicode=True,
            )[:50]

            if not base_slug:
                base_slug = secrets.token_hex(4)

            slug = base_slug
            counter = 1

            while True:
                exists = (
                    Business.objects.filter(
                        booking_slug=slug
                    )
                    .exclude(pk=business.pk)
                    .exists()
                )

                if not exists:
                    break

                slug = f"{base_slug}-{counter}"
                counter += 1

                if counter > 100:
                    slug = (
                        f"{base_slug}-{secrets.token_hex(3)}"
                    )
                    break

            business.booking_slug = slug
            business.save(
                update_fields=["booking_slug"]
            )

            logger.info(
                f"Admin reset booking slug for business "
                f"{business.id} to '{slug}' by "
                f"{request.session.get('dashboard_admin_phone')}"
            )

            messages.success(
                request,
                f'لینک رزرو به "{slug}" تغییر یافت.',
            )

        except Exception as e:
            logger.error(
                f"Reset slug error: {e}",
                exc_info=True,
            )
            messages.error(
                request,
                "خطا در تغییر لینک رزرو.",
            )

    return redirect(
        reverse(
            "dashboard:business_detail",
            kwargs={"business_id": business_id},
        )
    )


# ═══════════════════════════════════════════════
#   تایید کسب‌وکار (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_approve_view(request, business_id):
    """تایید کسب‌وکار"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    if request.method == "POST":
        business.status = Business.Status.APPROVED
        business.rejection_reason = ""
        business.save(
            update_fields=[
                "status",
                "rejection_reason",
            ]
        )

        DashboardCacheService.invalidate_dashboard_stats()
        DashboardAuditService.log_business_approved(
            request,
            business,
        )

        messages.success(
            request,
            f'کسب‌وکار "{business.name}" تایید شد.',
        )

        try:
            from apps.notifications.services import NotificationService

            NotificationService.send_business_approved(
                business
            )

        except Exception as e:
            logger.error(
                f"Failed to send approval notification: {e}"
            )

    return redirect(
        reverse(
            "dashboard:business_detail",
            kwargs={"business_id": business_id},
        )
    )


# ═══════════════════════════════════════════════
#   رد کسب‌وکار (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_reject_view(request, business_id):
    """رد کسب‌وکار"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    if request.method == "POST":
        reason = request.POST.get(
            "rejection_reason",
            "",
        ).strip()

        if not reason:
            messages.error(
                request,
                "دلیل رد کسب‌وکار الزامی است.",
            )
            return redirect(
                reverse(
                    "dashboard:business_detail",
                    kwargs={"business_id": business_id},
                )
            )

        business.status = Business.Status.REJECTED
        business.rejection_reason = reason
        business.save(
            update_fields=[
                "status",
                "rejection_reason",
            ]
        )

        DashboardCacheService.invalidate_dashboard_stats()
        DashboardAuditService.log_business_rejected(
            request,
            business,
            reason,
        )

        messages.warning(
            request,
            f'کسب‌وکار "{business.name}" رد شد.',
        )

        try:
            from apps.notifications.services import NotificationService

            NotificationService.send_business_rejected(
                business
            )

        except Exception as e:
            logger.error(
                f"Failed to send rejection notification: {e}"
            )

    return redirect(
        reverse(
            "dashboard:business_detail",
            kwargs={"business_id": business_id},
        )
    )


# ═══════════════════════════════════════════════
#   VIP (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_toggle_vip_view(request, business_id):
    """فعال/غیرفعال کردن VIP"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    if request.method == "POST":
        business.is_vip = not business.is_vip
        business.save(
            update_fields=["is_vip"]
        )

        DashboardCacheService.invalidate_dashboard_stats()
        DashboardAuditService.log_business_vip_toggled(
            request,
            business,
            business.is_vip,
        )

        status_text = (
            "VIP شد"
            if business.is_vip
            else "از VIP خارج شد"
        )

        messages.success(
            request,
            f'کسب‌وکار "{business.name}" {status_text}.',
        )

        try:
            from apps.notifications.services import NotificationService

            notification_body = (
                f'کسب‌وکار "{business.name}" '
                f'{"به لیست کسب‌وکارهای ویژه اضافه شد." if business.is_vip else "از لیست کسب‌وکارهای ویژه خارج شد."}'
            )

            NotificationService.send(
                user=business.owner,
                type="system",
                title=f"کسب‌وکار شما {status_text}",
                body=notification_body,
                data={"business_id": business.id},
                channels=["in_app"],
            )

        except Exception as e:
            logger.error(
                f"Failed to send VIP notification: {e}"
            )

    return redirect(
        reverse(
            "dashboard:business_detail",
            kwargs={"business_id": business_id},
        )
    )


# ═══════════════════════════════════════════════
#   مدیریت گالری (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_gallery_delete_view(
    request,
    business_id,
    gallery_id,
):
    """حذف تصویر گالری کسب‌وکار"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    gallery_item = get_object_or_404(
        BusinessGallery,
        id=gallery_id,
        business=business,
    )

    if request.method == "POST":
        try:
            if gallery_item.image:
                gallery_item.image.delete(
                    save=False
                )

            gallery_item.delete()

            messages.success(
                request,
                "تصویر از گالری حذف شد.",
            )

            logger.info(
                f"Admin deleted gallery image {gallery_id} "
                f"for business {business_id}"
            )

        except Exception as e:
            logger.error(
                f"Gallery delete error: {e}",
                exc_info=True,
            )
            messages.error(
                request,
                "خطا در حذف تصویر.",
            )

    return redirect(
        reverse(
            "dashboard:business_detail",
            kwargs={"business_id": business_id},
        )
    )


# ═══════════════════════════════════════════════
#   فعال/غیرفعال کردن خدمت (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_service_toggle_view(
    request,
    business_id,
    service_id,
):
    """فعال/غیرفعال کردن خدمت کسب‌وکار"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    service = get_object_or_404(
        Service,
        id=service_id,
        business=business,
    )

    if request.method == "POST":
        try:
            service.is_active = not service.is_active
            service.save(
                update_fields=["is_active"]
            )

            status_text = (
                "فعال"
                if service.is_active
                else "غیرفعال"
            )

            messages.success(
                request,
                f'خدمت "{service.name}" {status_text} شد.',
            )

            logger.info(
                f"Admin toggled service {service_id} "
                f"for business {business_id} "
                f"to {status_text}"
            )

        except Exception as e:
            logger.error(
                f"Service toggle error: {e}",
                exc_info=True,
            )
            messages.error(
                request,
                "خطا در تغییر وضعیت خدمت.",
            )

    return redirect(
        reverse(
            "dashboard:business_detail",
            kwargs={"business_id": business_id},
        )
    )


# ═══════════════════════════════════════════════
#   لغو نوبت کسب‌وکار (بدون تغییر از فاز ۳)
# ═══════════════════════════════════════════════

@role_required("app_admin", "super_admin")
@admin_login_required
def business_appointment_cancel_view(
    request,
    business_id,
    appointment_id,
):
    """لغو نوبت توسط ادمین"""

    business = get_object_or_404(
        Business,
        id=business_id,
    )

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        business=business,
    )

    if request.method == "POST":
        reason = request.POST.get(
            "reason",
            "لغو توسط ادمین",
        ).strip()

        if appointment.status != Appointment.Status.RESERVED:
            messages.error(
                request,
                "این نوبت قابل لغو نیست.",
            )
            return redirect(
                reverse(
                    "dashboard:business_detail",
                    kwargs={"business_id": business_id},
                )
            )

        try:
            from django.utils import timezone

            appointment.status = (
                Appointment.Status.CANCELLED_BY_SALON
            )
            appointment.cancellation_reason = reason
            appointment.cancelled_at = timezone.now()

            appointment.save(
                update_fields=[
                    "status",
                    "cancellation_reason",
                    "cancelled_at",
                    "updated_at",
                ]
            )

            # استرداد بیعانه در صورت وجود
            if appointment.deposit_amount > 0:
                try:
                    from apps.payments.services import process_refund

                    process_refund(appointment)

                except Exception as e:
                    logger.error(
                        f"Refund after admin cancel failed: {e}"
                    )

            messages.success(
                request,
                "نوبت لغو شد.",
            )

            logger.info(
                f"Admin cancelled appointment {appointment_id} "
                f"for business {business_id}"
            )

        except Exception as e:
            logger.error(
                f"Appointment cancel error: {e}",
                exc_info=True,
            )
            messages.error(
                request,
                "خطا در لغو نوبت.",
            )

    return redirect(
        reverse(
            "dashboard:business_detail",
            kwargs={"business_id": business_id},
        )
    )