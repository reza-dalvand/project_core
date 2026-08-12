"""
سرویس تسویه حساب
✅ هماهنگ با مدل‌های ساده‌سازی شده (Transaction + Settlement)
"""
import logging
from django.utils import timezone
from django.db.models import Sum, Case, When, Value, IntegerField

from apps.payments.models import Transaction, Settlement

logger = logging.getLogger(__name__)


class SettlementService:
    """سرویس تسویه خودکار"""

    # ═══════════════════════════════════════════════
    #   تسویه خودکار نوبت‌های انجام شده
    # ═══════════════════════════════════════════════
    @classmethod
    def auto_settle_completed_appointments(cls) -> int:
        """
        تسویه خودکار نوبت‌های انجام شده و تایید شده.
        تراکنش‌های DEPOSIT با status BLOCKED مربوط به نوبت‌های DONE
        به SETTLING تبدیل می‌شوند.
        """
        from apps.appointments.models import Appointment

        # پیدا کردن نوبت‌های انجام شده و تایید شده
        done_appointment_ids = Appointment.objects.filter(
            status=Appointment.Status.DONE,
            is_verified=True,
        ).values_list('id', flat=True)

        # پیدا کردن تراکنش‌های بیعانه بلوکه این نوبت‌ها
        txs = Transaction.objects.filter(
            appointment_id__in=done_appointment_ids,
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.BLOCKED,
        )

        processed = 0
        now = timezone.now()
        for tx in txs:
            try:
                tx.status = Transaction.Status.SETTLING
                tx.estimated_settlement = now + timezone.timedelta(days=1)
                tx.save(update_fields=['status', 'estimated_settlement'])
                processed += 1
            except Exception as e:
                logger.error(
                    f"Auto-settle failed for transaction {tx.id}: {e}"
                )

        logger.info(f"Auto-settle completed: {processed} transactions")
        return processed