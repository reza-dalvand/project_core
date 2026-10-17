"""
سیگنال‌های اپ businesses
"""
import logging

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models.signals import (
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver

from .models import Business

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Business)
def store_old_business_status(sender, instance, **kwargs):
    """
    ذخیره وضعیت قبلی قبل از save

    ✅ تغییر:
    - علاوه بر status، مقدار قبلی is_active هم ذخیره می‌شود
      تا حذف نرم کسب‌وکار تشخیص داده شود.
    """
    if instance.pk:
        try:
            old_instance = Business.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
            instance._old_is_active = getattr(old_instance, "is_active", None)
        except Business.DoesNotExist:
            instance._old_status = None
            instance._old_is_active = None
    else:
        instance._old_status = None
        instance._old_is_active = None


@receiver(post_save, sender=Business)
def business_status_changed(sender, instance, created, **kwargs):
    """
    تشخیص تغییر وضعیت کسب‌وکار و ارسال اعلان
    """
    if created:
        logger.info(f"New business created: {instance.name}")
        return

    old_status = getattr(instance, "_old_status", None)
    if old_status is None or old_status == instance.status:
        return

    logger.info(
        f"Business status changed: {instance.name} "
        f"from {old_status} to {instance.status}"
    )

    if (
        instance.status == Business.Status.APPROVED
        and old_status != Business.Status.APPROVED
    ):
        try:
            from apps.notifications.services import NotificationService

            NotificationService.send_business_approved(instance)
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")

    elif (
        instance.status == Business.Status.REJECTED
        and old_status != Business.Status.REJECTED
    ):
        try:
            from apps.notifications.services import NotificationService

            NotificationService.send_business_rejected(instance)
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {e}")


@receiver(post_save, sender=Business)
def cleanup_business_ad_banners_on_soft_delete(sender, instance, created, **kwargs):
    """
    ✅ قابلیت مورد نظر:
    اگر کسب‌وکار به‌صورت نرم حذف شد، یعنی is_active از True به False تغییر کرد،
    تمام بنرهای لینک‌شده به آن کسب‌وکار نیز حذف می‌شوند.

    این سیگنال هر دو مسیر زیر را پوشش می‌دهد:
    - حذف کسب‌وکار از API: BusinessDeleteView
    - حذف کسب‌وکار از داشبورد: business_delete_view
    """
    if created or kwargs.get("raw"):
        return

    old_is_active = getattr(instance, "_old_is_active", None)
    current_is_active = getattr(instance, "is_active", None)

    if old_is_active is True and current_is_active is False:
        _purge_business_ad_banners(instance)


@receiver(pre_delete, sender=Business)
def store_business_banner_files_before_hard_delete(sender, instance, **kwargs):
    """
    برای حذف سخت کسب‌وکار:
    قبل از حذف رکورد، نام فایل تصاویر بنرهای مرتبط ذخیره می‌شود
    تا بعد از commit، فایل‌های اضافی از استوریج پاک شوند.

    نکته:
    خود رکوردهای AdBanner به دلیل on_delete=CASCADE حذف می‌شوند،
    اما فایل‌های تصویر به‌صورت پیش‌فرض حذف نمی‌شوند.
    """
    if kwargs.get("raw"):
        instance._banner_image_names_before_delete = []
        return

    try:
        instance._banner_image_names_before_delete = list(
            instance.ad_banners.values_list("image", flat=True)
        )
    except Exception as exc:
        logger.warning(
            "Failed to collect banner image names before deleting business %s: %s",
            instance.pk,
            exc,
        )
        instance._banner_image_names_before_delete = []


@receiver(post_delete, sender=Business)
def cleanup_business_banner_files_after_hard_delete(sender, instance, **kwargs):
    """
    بعد از حذف موفق کسب‌وکار، فایل‌های تصویر بنرهای مرتبط پاک می‌شوند.
    """
    if kwargs.get("raw"):
        return

    image_names = getattr(instance, "_banner_image_names_before_delete", [])
    if image_names:
        transaction.on_commit(
            lambda names=image_names: _delete_banner_files(names)
        )


def _purge_business_ad_banners(business):
    """
    حذف بنرهای مرتبط با کسب‌وکار در زمان حذف نرم.

    ترتیب ایمن:
    1. ابتدا رکوردهای دیتابیس حذف می‌شوند.
    2. سپس حذف فایل‌های تصویر به after-commit موکول می‌شود.
       این کار باعث می‌شود اگر ترنزاکشن rollback شد، فایل‌ها اشتباهاً پاک نشوند.
    """
    banners = list(business.ad_banners.all())
    if not banners:
        return

    banner_ids = [banner.id for banner in banners]

    # حذف رکوردهای بنر از دیتابیس
    business.ad_banners.filter(id__in=banner_ids).delete()

    # جمع‌آوری نام فایل‌ها برای حذف بعد از commit
    image_names = [
        banner.image.name
        for banner in banners
        if banner.image and banner.image.name
    ]

    if image_names:
        transaction.on_commit(
            lambda names=image_names: _delete_banner_files(names)
        )

    logger.info(
        "Soft-deleted business %s: removed %s linked ad banner(s).",
        business.pk,
        len(banners),
    )


def _delete_banner_files(image_names):
    """
    حذف فیزیکی فایل‌های تصویر بنر از استوریج.
    خطای حذف فایل نباید عملیات اصلی را با مشکل مواجه کند، فقط لاگ می‌شود.
    """
    for name in image_names:
        if not name:
            continue

        try:
            default_storage.delete(name)
        except Exception as exc:
            logger.warning(
                "Failed to delete banner image file '%s': %s",
                name,
                exc,
            )