"""
سرویس یکپارچه نوتیفیکیشن
ارسال اعلان از طریق SMS (کاوه‌نگار) + In-App
"""
import logging
from django.conf import settings
from django.template import Template, Context
from django.utils import timezone

from .models import Notification, SMSTemplate, SMSLog, PushDevice

logger = logging.getLogger(__name__)


class NotificationService:
    """
    سرویس اصلی ارسال اعلان‌ها

    روش‌های ارسال:
    - in_app: فقط اعلان داخلی اپ
    - sms: فقط پیامک
    - push: فقط Push (فعلاً stub)
    - all: همه روش‌ها
    """

    # ══════════════════════════════════════════
    #    ارسال عمومی
    # ══════════════════════════════════════════

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
        """
        ارسال اعلان از طریق کانال‌های مختلف

        Args:
            user: کاربر مقصد
            type: نوع اعلان (از Notification.Type)
            title: عنوان
            body: متن
            data: داده‌های تکمیلی (JSON)
            channels: لیست کانال‌ها ['in_app', 'sms', 'push']
            sms_template_type: نوع قالب پیامک
            sms_variables: متغیرهای قالب پیامک

        Returns:
            dict: نتیجه ارسال هر کانال
        """
        if channels is None:
            channels = ['in_app']

        results = {
            'in_app': False,
            'sms': False,
            'push': False,
        }

        # ─── In-App Notification ───
        if 'in_app' in channels:
            try:
                notification = Notification.objects.create(
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

        # ─── SMS Notification ───
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

        # ─── Push Notification (stub) ───
        if 'push' in channels:
            try:
                push_result = cls._send_push(user, title, body, data)
                results['push'] = push_result
            except Exception as e:
                logger.error(f"Push notification failed: {e}")

        return results

    # ══════════════════════════════════════════
    #    ارسال پیامک
    # ══════════════════════════════════════════

    @classmethod
    def send_sms(
        cls,
        phone: str,
        template_type: str,
        variables: dict = None,
        user=None,
    ) -> dict:
        """
        ارسال پیامک از طریق کاوه‌نگار

        Args:
            phone: شماره موبایل
            template_type: نوع قالب (از SMSTemplate.Type)
            variables: متغیرهای قالب
            user: کاربر (برای لاگ)

        Returns:
            dict: {'success': bool, 'message_id': str, 'cost': int}
        """
        variables = variables or {}

        # دریافت قالب
        try:
            template = SMSTemplate.objects.get(
                type=template_type,
                is_active=True,
            )
        except SMSTemplate.DoesNotExist:
            logger.error(f"SMS template not found: {template_type}")
            return {'success': False, 'error': 'Template not found'}

        # ساخت متن پیام
        try:
            django_template = Template(template.pattern)
            message = django_template.render(Context(variables))
        except Exception as e:
            logger.error(f"SMS template render error: {e}")
            message = template.pattern

        # ایجاد لاگ
        sms_log = SMSLog.objects.create(
            phone=phone,
            user=user,
            template=template,
            message=message,
            variables=variables,
            status=SMSLog.Status.PENDING,
        )

        # ارسال واقعی
        try:
            api_key = getattr(settings, 'KAVENEGAR_API_KEY', '')

            if api_key:
                from kavenegar import KavenegarAPI
                api = KavenegarAPI(api_key)

                params = {
                    'receptor': phone,
                    'template': template.provider_template_id,
                    **variables,
                }

                response = api.VerifyLookup(params)
                message_id = str(response['entries']['messageid'])
                cost = response['entries'].get('cost', 0)

                sms_log.status = SMSLog.Status.SENT
                sms_log.provider_message_id = message_id
                sms_log.cost = cost
                sms_log.save()

                logger.info(f"SMS sent to {phone}: {message_id}")
                return {
                    'success': True,
                    'message_id': message_id,
                    'cost': cost,
                }
            else:
                # حالت توسعه
                print(f"\n📱 [SMS to {phone}]")
                print(f"   Template: {template.name}")
                print(f"   Message: {message}\n")

                sms_log.status = SMSLog.Status.SENT
                sms_log.save()

                return {
                    'success': True,
                    'message_id': 'dev_mock',
                    'cost': 0,
                }

        except Exception as e:
            logger.error(f"SMS send error to {phone}: {e}")
            sms_log.status = SMSLog.Status.FAILED
            sms_log.error_message = str(e)
            sms_log.save()
            return {'success': False, 'error': str(e)}

    # ══════════════════════════════════════════
    #    Push Notification (Stub)
    # ══════════════════════════════════════════

    @classmethod
    def _send_push(cls, user, title: str, body: str, data: dict = None) -> bool:
        """
        ارسال Push Notification (فعلاً stub)
        در آینده با FCM/APNs پیاده‌سازی می‌شود
        """
        devices = PushDevice.objects.filter(
            user=user,
            is_active=True,
        )

        if not devices.exists():
            return False

        for device in devices:
            print(f"\n🔔 [Push to {device.device_name}]")
            print(f"   Title: {title}")
            print(f"   Body: {body}")
            print(f"   Token: {device.token[:20]}...\n")

        return True

    # ══════════════════════════════════════════
    #    اعلان‌های از پیش تعریف شده
    # ══════════════════════════════════════════

    @classmethod
    def send_booking_confirmed(cls, appointment):
        """اعلان تایید رزرو"""
        from apps.core.utils import to_persian_digits

        return cls.send(
            user=appointment.customer,
            type=Notification.Type.BOOKING_CONFIRMED,
            title='رزرو شما تایید شد ✅',
            body=(
                f'رزرو {appointment.service.name} در '
                f'{appointment.business.name} برای '
                f'{to_persian_digits(str(appointment.date))} '
                f'ساعت {to_persian_digits(str(appointment.time))} تایید شد.'
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
                'date': str(appointment.date),
                'time': str(appointment.time),
                'code': appointment.verification_code,
            },
        )

    @classmethod
    def send_booking_reminder(cls, appointment):
        """یادآوری نوبت (۲۴ ساعت قبل)"""
        return cls.send(
            user=appointment.customer,
            type=Notification.Type.BOOKING_REMINDER,
            title='یادآوری نوبت فردا ⏰',
            body=(
                f'فردا ساعت {appointment.time} نوبت '
                f'{appointment.service.name} در '
                f'{appointment.business.name} دارید.'
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
                'date': str(appointment.date),
                'time': str(appointment.time),
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
                f'نوبت {appointment.service.name} در '
                f'{appointment.business.name} لغو شد. '
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
                'date': str(appointment.date),
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
            user=transaction.user,
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
            user=transaction.user,
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
                f'{review.customer.full_name or review.customer.phone} '
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

    @classmethod
    def send_verification_code(cls, user, code: str):
        """ارسال کد تایید نوبت"""
        return cls.send(
            user=user,
            type=Notification.Type.SYSTEM,
            title='کد تایید نوبت',
            body=f'کد تایید نوبت شما: {code}',
            channels=['sms'],
            sms_template_type=SMSTemplate.Type.VERIFICATION_CODE,
            sms_variables={
                'code': code,
            },
        )

    # ══════════════════════════════════════════
    #    مدیریت اعلان‌ها
    # ══════════════════════════════════════════

    @classmethod
    def mark_as_read(cls, user, notification_id: int = None) -> int:
        """
        علامت‌گذاری اعلان به عنوان خوانده شده
        اگر notification_id=None باشد، همه اعلان‌ها خوانده می‌شوند
        """
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