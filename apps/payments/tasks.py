"""
وظایف Celery برای پردازش‌های پس‌زمینه مالی
✅ هماهنگ با مدل‌های واقعی
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def auto_settle_completed_appointments(self):
    """
    تسویه خودکار نوبت‌های انجام شده
    هر ۱ ساعت اجرا می‌شود
    """
    from apps.payments.services.settlement_service import SettlementService
    try:
        processed = SettlementService.auto_settle_completed_appointments()
        logger.info(f"Auto-settle task completed: {processed} transactions")
        return {'processed': processed}
    except Exception as exc:
        logger.error(f"Auto-settle task failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def process_pending_settlements(self):
    """
    پردازش تسویه‌های در انتظار (خودکار)
    هر ۶ ساعت اجرا می‌شود
    """
    from apps.payments.models import Settlement
    from apps.payments.services.payment_service import PaymentService
    try:
        settlements = Settlement.objects.filter(
            status=Settlement.Status.PENDING,
            created_at__lte=timezone.now() - timedelta(hours=24),
        )
        processed = 0
        for settlement in settlements:
            try:
                PaymentService.process_settlement(settlement)
                processed += 1
            except Exception as e:
                logger.error(
                    f"Auto-process settlement {settlement.id} failed: {e}"
                )
        logger.info(f"Auto-process settlements: {processed} processed")
        return {'processed': processed}
    except Exception as exc:
        logger.error(f"Process settlements task failed: {exc}")
        raise self.retry(exc=exc, countdown=600)