"""
سرویس یکپارچه نوتیفیکیشن
ارسال اعلان از طریق SMS (کاوه‌نگار) + In-App

متدهای کاوه‌نگار:
- verify_lookup: فقط برای پترن‌های احراز هویت (مثل کد تایید)
- sms_send: ارسال پیام ساده (برای اطلاع‌رسانی مثل رزرو)
- sms_sendarray: ارسال گروهی (برای تبلیغات)
"""
import logging
from django.conf import settings
from django.template import Template, Context
from django.utils import timezone
from .models import Notification, SMSTemplate, SMSLog

logger = logging.getLogger(__name__)


class NotificationService:
    """سرویس اصلی ارسال اعلان‌ها"""

    @classmethod
    def send(
        cls,
        user,
        type: str,
        title: str,
        body: str,
        data: dict = None,
        channels: list = None,
        sms_template_type: str = None,
        sms_variables: dict = None,
    ) -> dict:
        """ارسال اعلان از طریق کانال‌های مختلف"""
        if channels is None:
            channels = ['in_app']

        results = {
            'in_app': False,
            'sms': False,
            'push': False,
        }

        # In-App Notification
        if 'in_app' in channels:
            try:
                Notification.objects.create(
                    user=user,
                    type=type,
                    title=title,
                    body=body,
                    data=data or {},
                )
                results['in_app'] = True
                logger.info(f"In-app notification sent to {user.phone}: {title}")
            except Exception as e:
                logger.error(f"In-app notification failed: {e}")

        # SMS Notification
        if 'sms' in channels and sms_template_type:
            try:
                sms_result = cls.send_sms(
                    phone=user.phone,
                    template_type=sms_template_type,
                    variables=sms_variables or {},
                    user=user,
                )
                results['sms'] = sms_result.get('success', False)
            except Exception as e:
                logger.error(f"SMS notification failed: {e}")

        return results

    @classmethod
    def send_sms(
        cls,
        phone: str,
        template_type: str,
        variables: dict = None,
        user=None,
    ) -> dict:
        """
        ارسال پیامک بر اساس قالب
        روش ارسال بر اساس فیلد send_method قالب تعیین می‌شود:
        - otp: verify_lookup (پترن احراز هویت)
        - simple: sms_send (پیام ساده)
        """
        variables = variables or {}

        try:
            template = SMSTemplate.objects.get(
                type=template_type,
                is_active=True,
            )
        except SMSTemplate.DoesNotExist:
            logger.error(f"SMS template not found: {template_type}")
            return {'success': False, 'error': 'Template not found'}

        # ایجاد لاگ
        sms_log = SMSLog.objects.create(
            phone=phone,
            user=user,
            template=template,
            message='',
            variables=variables,
            status=SMSLog.Status.PENDING,
        )

        try:
            from shared.sms import get_sms_provider
            provider = get_sms_provider()

            # ─── روش ارسال بر اساس فیلد قالب ───
            if template.send_method == SMSTemplate.SendMethod.OTP:
                # پترن احراز هویت (مثل کد تایید)
                result = provider.send_pattern(
                    phone=phone,
                    template_name=template.provider_template_id,
                    **variables,
                )
            else:
                # پیام ساده (مثل رزرو)
                try:
                    django_template = Template(template.pattern)
                    message = django_template.render(Context(variables))
                except Exception as e:
                    logger.error(f"SMS template render error: {e}")
                    message = template.pattern

                result = provider.send(
                    phone=phone,
                    message=message,
                )

            if result.success:
                sms_log.status = SMSLog.Status.SENT
                sms_log.provider_message_id = result.message_id
                sms_log.cost = result.cost
                sms_log.save()
                return {
                    'success': True,
                    'message_id': result.message_id,
                    'cost': result.cost,
                }
            else:
                sms_log.status = SMSLog.Status.FAILED
                sms_log.error_message = result.error_message
                sms_log.save()
                return {
                    'success': False,
                    'error': result.error_message,
                }

        except Exception as e:
            logger.error(f"SMS send error to {phone}: {e}")
            sms_log.status = SMSLog.Status.FAILED
            sms_log.error_message = str(e)
            sms_log.save()
            return {'success': False, 'error': str(e)}

    @classmethod
    def send_bulk_sms(
        cls,
        recipients: list,
        message: str,
        sender: str = '',
        user=None,
    ) -> dict:
        """
        ارسال گروهی پیامک (برای تبلیغات)
        """
        if not recipients:
            return {'success': False, 'error': 'لیست دریافت‌کنندگان خالی است'}

        try:
            from shared.sms import get_sms_provider
            provider = get_sms_provider()

            result = provider.send_bulk(
                recipients=recipients,
                messages=[message],
                senders=[sender] if sender else None,
            )

            return {
                'success': result.success,
                'total_sent': result.total_sent,
                'total_failed': result.total_failed,
                'total_cost': result.total_cost,
            }

        except Exception as e:
            logger.error(f"Bulk SMS send error: {e}")
            return {'success': False, 'error': str(e)}

    # ═══════════════════════════════════════════════
    #   اعلان‌های از پیش تعریف شده
    # ═══════════════════════════════════════════════

    @classmethod
    def send_booking_confirmed(cls, appointment):
        """اعلان تایید رزرو"""
        return cls.send(
            user=appointment.customer,
            type=Notification.Type.BOOKING_CONFIRMED,
            title='رزرو شما تایید شد ✅',
            body=(
                f'رزرو {appointment.service.name} در '
                f'{appointment.business.name} برای '
                f'{appointment.date_key} '
                f'ساعت {appointment.time_slot} تایید شد.'
            ),
            data={
                'appointment_id': appointment.id,
                'business_id': appointment.business_id,
            },
            channels=['in_app', 'sms'],
            sms_template_type=SMSTemplate.Type.BOOKING_CONFIRMED,
            sms_variables={
                'business_name': appointment.business.name,
                'service_name': appointment.service.name,
                'date': appointment.date_key,
                'time': str(appointment.time_slot),
                'code': appointment.verification_code,
            },
        )

    @classmethod
    def send_booking_reminder(cls, appointment):
        """یادآوری نوبت"""
        return cls.send(
            user=appointment.customer,
            type=Notification.Type.BOOKING_REMINDER,
            title='یادآوری نوبت ⏰',
            body=(
                f'نوبت {appointment.service.name} '
                f'در {appointment.business.name} '
                f'برای {appointment.date_key} ساعت {appointment.time_slot} دارید.'
            ),
            data={
                'appointment_id': appointment.id,
                'business_id': appointment.business_id,
            },
            channels=['in_app', 'sms'],
            sms_template_type=SMSTemplate.Type.BOOKING_REMINDER,
            sms_variables={
                'business_name': appointment.business.name,
                'service_name': appointment.service.name,
                'date': appointment.date_key,
                'time': str(appointment.time_slot),
            },
        )

    @classmethod
    def send_booking_cancelled(cls, appointment, reason: str = ''):
        """اعلان لغو نوبت"""
        return cls.send(
            user=appointment.customer,
            type=Notification.Type.BOOKING_CANCELLED,
            title='نوبت شما لغو شد ❌',
            body=(
                f'نوبت {appointment.service.name} '
                f'در {appointment.business.name} لغو شد. '
                f'{"دلیل: " + reason if reason else ""}'
            ),
            data={
                'appointment_id': appointment.id,
                'reason': reason,
            },
            channels=['in_app', 'sms'],
            sms_template_type=SMSTemplate.Type.BOOKING_CANCELLED,
            sms_variables={
                'business_name': appointment.business.name,
                'service_name': appointment.service.name,
                'date': appointment.date_key,
            },
        )

    @classmethod
    def send_booking_done(cls, appointment):
        """اعلان انجام خدمت"""
        return cls.send(
            user=appointment.customer,
            type=Notification.Type.BOOKING_DONE,
            title='خدمت انجام شد ✅',
            body=(
                f'{appointment.service.name} در '
                f'{appointment.business.name} با موفقیت انجام شد. '
                f'لطفاً نظر خود را ثبت کنید.'
            ),
            data={
                'appointment_id': appointment.id,
                'business_id': appointment.business_id,
            },
            channels=['in_app'],
        )

    @classmethod
    def send_payment_success(cls, transaction):
        """اعلان پرداخت موفق"""
        from apps.core.utils import format_price
        return cls.send(
            user=transaction.customer,
            type=Notification.Type.PAYMENT_SUCCESS,
            title='پرداخت موفق 💳',
            body=(
                f'پرداخت {format_price(transaction.amount)} '
                f'با موفقیت انجام شد. '
                f'کد پیگیری: {transaction.tracking_code}'
            ),
            data={
                'transaction_id': transaction.id,
                'tracking_code': transaction.tracking_code,
            },
            channels=['in_app', 'sms'],
            sms_template_type=SMSTemplate.Type.PAYMENT_SUCCESS,
            sms_variables={
                'amount': str(transaction.amount),
                'tracking_code': transaction.tracking_code,
            },
        )

    @classmethod
    def send_payment_refunded(cls, transaction, amount: int):
        """اعلان استرداد وجه"""
        from apps.core.utils import format_price
        return cls.send(
            user=transaction.customer,
            type=Notification.Type.PAYMENT_REFUNDED,
            title='استرداد وجه 💰',
            body=(
                f'مبلغ {format_price(amount)} '
                f'به حساب شما واریز شد.'
            ),
            data={
                'transaction_id': transaction.id,
                'refund_amount': amount,
            },
            channels=['in_app', 'sms'],
            sms_template_type=SMSTemplate.Type.REFUND_COMPLETED,
            sms_variables={
                'amount': str(amount),
            },
        )

    @classmethod
    def send_settlement_completed(cls, settlement):
        """اعلان تسویه حساب"""
        from apps.core.utils import format_price
        return cls.send(
            user=settlement.business.owner,
            type=Notification.Type.SETTLEMENT_COMPLETED,
            title='تسویه حساب انجام شد 💰',
            body=(
                f'مبلغ {format_price(settlement.amount)} '
                f'به حساب بانکی شما واریز شد.'
            ),
            data={
                'settlement_id': settlement.id,
                'amount': settlement.amount,
            },
            channels=['in_app', 'sms'],
        )

    @classmethod
    def send_new_review(cls, review):
        """اعلان نظر جدید به کسب‌وکار"""
        return cls.send(
            user=review.business.owner,
            type=Notification.Type.NEW_REVIEW,
            title='نظر جدید دریافت شد ⭐',
            body=(
                f'{review.customer.full_name} '
                f'به کسب‌وکار شما {review.rating} ستاره داد.'
            ),
            data={
                'review_id': review.id,
                'rating': review.rating,
            },
            channels=['in_app'],
        )

    @classmethod
    def send_business_approved(cls, business):
        """اعلان تایید کسب‌وکار"""
        return cls.send(
            user=business.owner,
            type=Notification.Type.BUSINESS_APPROVED,
            title='کسب‌وکار شما تایید شد 🎉',
            body=(
                f'تبریک! کسب‌وکار "{business.name}" '
                f'تایید شد و اکنون فعال است.'
            ),
            data={
                'business_id': business.id,
            },
            channels=['in_app', 'sms'],
            sms_template_type=SMSTemplate.Type.BUSINESS_APPROVED,
            sms_variables={
                'business_name': business.name,
            },
        )

    @classmethod
    def send_business_rejected(cls, business):
        """اعلان رد کسب‌وکار"""
        return cls.send(
            user=business.owner,
            type=Notification.Type.BUSINESS_REJECTED,
            title='کسب‌وکار شما تایید نشد ⚠️',
            body=(
                f'متاسفانه کسب‌وکار "{business.name}" تایید نشد. '
                f'دلیل: {business.rejection_reason}'
            ),
            data={
                'business_id': business.id,
                'reason': business.rejection_reason,
            },
            channels=['in_app', 'sms'],
            sms_template_type=SMSTemplate.Type.BUSINESS_REJECTED,
            sms_variables={
                'business_name': business.name,
                'reason': business.rejection_reason,
            },
        )

    # ═══════════════════════════════════════════════
    #   مدیریت اعلان‌ها
    # ═══════════════════════════════════════════════

    @classmethod
    def mark_as_read(cls, user, notification_id: int = None) -> int:
        """علامت‌گذاری اعلان به عنوان خوانده شده"""
        qs = Notification.objects.filter(user=user, is_read=False)
        if notification_id:
            qs = qs.filter(id=notification_id)
        count = qs.update(
            is_read=True,
            read_at=timezone.now(),
        )
        return count

    @classmethod
    def get_unread_count(cls, user) -> int:
        """تعداد اعلان‌های خوانده نشده"""
        return Notification.objects.filter(
            user=user,
            is_read=False,
        ).count()

    @classmethod
    def delete_old_notifications(cls, days: int = 90) -> int:
        """حذف اعلان‌های قدیمی"""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        count, _ = Notification.objects.filter(
            created_at__lt=cutoff,
            is_read=True,
        ).delete()
        return count