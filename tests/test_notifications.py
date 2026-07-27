"""
تست‌های سیستم نوتیفیکیشن
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from apps.notifications.models import Notification, SMSTemplate, SMSLog
from apps.notifications.services import NotificationService


@pytest.fixture
def sms_templates(db):
    """ایجاد قالب‌های پیامک تست"""
    templates = {}
    for type_choice in SMSTemplate.Type.choices:
        template = SMSTemplate.objects.create(
            type=type_choice[0],
            name=f'قالب {type_choice[1]}',
            provider_template_id=f'test-{type_choice[0]}',
            pattern='متن تست: {{ code }}',
            variables=['code'],
            is_active=True,
        )
        templates[type_choice[0]] = template
    return templates


@pytest.mark.django_db
class TestNotificationService:
    """تست‌های NotificationService"""

    def test_send_in_app_notification(self, customer_user):
        """تست ارسال اعلان داخلی"""
        result = NotificationService.send(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='تست',
            body='متن تست',
            channels=['in_app'],
        )

        assert result['in_app'] is True
        assert Notification.objects.filter(user=customer_user).count() == 1

        notification = Notification.objects.first()
        assert notification.title == 'تست'
        assert notification.body == 'متن تست'
        assert notification.is_read is False

    def test_send_sms_notification(self, customer_user, sms_templates, settings):
        """تست ارسال پیامک"""
        # ✅ اضافه شد: غیرفعال کردن API Key واقعی برای استفاده از Mock داخلی
        settings.KAVENEGAR_API_KEY = ''

        result = NotificationService.send_sms(
            phone=customer_user.phone,
            template_type=SMSTemplate.Type.OTP_LOGIN,
            variables={'code': '12345'},
            user=customer_user,
        )
        assert result['success'] is True
        assert SMSLog.objects.filter(phone=customer_user.phone).count() == 1


    def test_mark_as_read(self, customer_user):
        """تست علامت‌گذاری خوانده شده"""
        # ایجاد ۳ اعلان
        for i in range(3):
            Notification.objects.create(
                user=customer_user,
                type=Notification.Type.SYSTEM,
                title=f'تست {i}',
                body='متن',
            )

        assert NotificationService.get_unread_count(customer_user) == 3

        # خوانده کردن همه
        count = NotificationService.mark_as_read(customer_user)
        assert count == 3
        assert NotificationService.get_unread_count(customer_user) == 0

    def test_get_unread_count(self, customer_user):
        """تست تعداد اعلان‌های خوانده نشده"""
        Notification.objects.create(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='خوانده نشده',
            body='متن',
            is_read=False,
        )
        Notification.objects.create(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='خوانده شده',
            body='متن',
            is_read=True,
        )

        assert NotificationService.get_unread_count(customer_user) == 1

    def test_delete_old_notifications(self, customer_user):
        """تست حذف اعلان‌های قدیمی"""
        # ایجاد اعلان قدیمی
        old_notification = Notification.objects.create(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='قدیمی',
            body='متن',
            is_read=True,
        )
        # تغییر تاریخ به ۱۰۰ روز پیش
        Notification.objects.filter(id=old_notification.id).update(
            created_at=timezone.now() - timedelta(days=100)
        )

        # ایجاد اعلان جدید
        Notification.objects.create(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='جدید',
            body='متن',
            is_read=True,
        )

        count = NotificationService.delete_old_notifications(days=90)
        assert count == 1
        assert Notification.objects.count() == 1


@pytest.mark.django_db
class TestNotificationAPI:
    """تست‌های API نوتیفیکیشن"""

    def test_notification_list(self, authenticated_customer_client, customer_user):
        """تست لیست اعلان‌ها"""
        Notification.objects.create(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='تست',
            body='متن',
        )

        response = authenticated_customer_client.get(
            '/api/v1/notifications/'
        )

        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_notification_count(self, authenticated_customer_client, customer_user):
        """تست تعداد اعلان‌ها"""
        Notification.objects.create(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='تست',
            body='متن',
            is_read=False,
        )

        response = authenticated_customer_client.get(
            '/api/v1/notifications/count/'
        )

        assert response.status_code == 200
        data = response.json()['data']
        assert data['unread'] == 1
        assert data['total'] == 1

    def test_mark_as_read(self, authenticated_customer_client, customer_user):
        """تست خوانده شده"""
        Notification.objects.create(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='تست',
            body='متن',
            is_read=False,
        )

        response = authenticated_customer_client.post(
            '/api/v1/notifications/mark-read/',
            {},
            format='json',
        )

        assert response.status_code == 200
        assert Notification.objects.filter(is_read=False).count() == 0

    def test_delete_notification(self, authenticated_customer_client, customer_user):
        """تست حذف اعلان"""
        notification = Notification.objects.create(
            user=customer_user,
            type=Notification.Type.SYSTEM,
            title='تست',
            body='متن',
        )

        response = authenticated_customer_client.delete(
            f'/api/v1/notifications/{notification.id}/'
        )

        assert response.status_code == 200
        assert Notification.objects.count() == 0


@pytest.mark.django_db
class TestCeleryTasks:
    """تست‌های Celery Tasks"""

    def test_check_expired_transactions(self, customer_user):  # ✅ اضافه شدن customer_user
        """تست بررسی تراکنش‌های منقضی"""
        from apps.payments.models import Transaction
        from apps.notifications.tasks import check_expired_pending_transactions

        # ایجاد تراکنش قدیمی PENDING
        tx = Transaction.objects.create(
            user=customer_user,  # ✅ اصلاح شد: استفاده از کاربر واقعی به جای user_id=1
            type=Transaction.Type.DEPOSIT,
            status=Transaction.Status.PENDING,
            amount=100000,
        )
        Transaction.objects.filter(id=tx.id).update(
            created_at=timezone.now() - timedelta(minutes=35)
        )
        result = check_expired_pending_transactions()
        assert result['expired'] >= 1


    def test_cleanup_old_otp_codes(self, customer_user):
        """تست پاکسازی کدهای OTP قدیمی"""
        from apps.accounts.models import OTP
        from apps.notifications.tasks import cleanup_old_otp_codes

        # ایجاد OTP قدیمی
        otp = OTP.objects.create(
            phone=customer_user.phone,
            code='12345',
            purpose=OTP.Purpose.LOGIN,
            is_used=True,
            expires_at=timezone.now() - timedelta(days=2),
        )
        OTP.objects.filter(id=otp.id).update(
            created_at=timezone.now() - timedelta(days=2)
        )

        result = cleanup_old_otp_codes()
        assert result['deleted'] >= 1