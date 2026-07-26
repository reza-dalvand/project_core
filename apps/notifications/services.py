"""
سرویس‌های ارسال پیامک و اعلان
"""
import logging
from django.conf import settings
from django.template import Template, Context
from .models import SMSTemplate, SMSLog, Notification

logger = logging.getLogger(__name__)


class SMSService:
    """سرویس ارسال پیامک (فعلاً با کاوه‌نگار)"""

    @staticmethod
    def send(phone, template_type, variables=None):
        """
        ارسال پیامک بر اساس نوع قالب

        مثال:
            SMSService.send('09121234567', 'otp_login', {'code': '12345'})
        """
        variables = variables or {}

        try:
            template = SMSTemplate.objects.get(
                type=template_type,
                is_active=True,
            )
        except SMSTemplate.DoesNotExist:
            logger.error(f'SMS template not found: {template_type}')
            return None

        # ساخت پیام با جایگزینی متغیرها
        try:
            django_template = Template(template.pattern)
            message = django_template.render(Context(variables))
        except Exception as e:
            logger.error(f'SMS template render error: {e}')
            message = template.pattern

        # ساخت لاگ
        sms_log = SMSLog.objects.create(
            phone=phone,
            template=template,
            message=message,
            variables=variables,
            status=SMSLog.Status.PENDING,
        )

        try:
            # ─── ارسال واقعی با کاوه‌نگار ───
            if hasattr(settings, 'KAVENEGAR_API_KEY') and settings.KAVENEGAR_API_KEY:
                from kavenegar import KavenegarAPI, APIException, HTTPException
                api = KavenegarAPI(settings.KAVENEGAR_API_KEY)
                params = {
                    'receptor': phone,
                    'template': template.provider_template_id,
                    **variables,
                }
                response = api.VerifyLookup(params)
                sms_log.provider_message_id = str(response['entries']['messageid'])
                sms_log.status = SMSLog.Status.SENT
                sms_log.cost = response['entries']['cost']
                sms_log.save()
                logger.info(f'SMS sent to {phone}: {sms_log.provider_message_id}')
            else:
                # ─── حالت توسعه: فقط چاپ در کنسول ───
                print(f'\n📱 [SMS to {phone}]')
                print(f'   Template: {template.name}')
                print(f'   Message: {message}\n')
                sms_log.status = SMSLog.Status.SENT
                sms_log.save()

            return sms_log

        except Exception as e:
            logger.error(f'SMS send error to {phone}: {e}')
            sms_log.status = SMSLog.Status.FAILED
            sms_log.error_message = str(e)
            sms_log.save()
            return sms_log


class NotificationService:
    """سرویس ارسال اعلان داخلی و Push"""

    @staticmethod
    def send(user, type, title, body, data=None, send_push=True):
        """
        ارسال اعلان داخلی + Push

        مثال:
            NotificationService.send(
                user=user,
                type='booking_confirmed',
                title='رزرو شما تایید شد',
                body='رزرو فیشیال تخصصی در سالن نیلارام تایید شد',
                data={'appointment_id': 123},
            )
        """
        notification = Notification.objects.create(
            user=user,
            type=type,
            title=title,
            body=body,
            data=data or {},
        )

        if send_push:
            try:
                NotificationService._send_push(notification)
                notification.is_pushed = True
                notification.save(update_fields=['is_pushed'])
            except Exception as e:
                logger.error(f'Push send error: {e}')

        return notification

    @staticmethod
    def _send_push(notification):
        """ارسال Push Notification به دستگاه‌های کاربر"""
        from .models import PushDevice

        devices = PushDevice.objects.filter(
            user=notification.user,
            is_active=True,
        )

        if not devices.exists():
            return

        # ─── اینجا می‌توان Firebase Cloud Messaging (FCM) یا APNs را پیاده‌سازی کرد ───
        # فعلاً فقط لاگ می‌گیریم
        for device in devices:
            print(f'\n🔔 [Push to {device.device_name}]')
            print(f'   Title: {notification.title}')
            print(f'   Body: {notification.body}')
            print(f'   Token: {device.token[:20]}...\n')