"""
تست‌های یادآوری تمدید
"""
import pytest
import jdatetime
from django.utils import timezone

from apps.reminders.models import RenewalReminder


@pytest.mark.django_db
class TestRenewalReminder:
    def test_create_reminder(
        self, customer_user, approved_business, test_service
    ):
        from apps.appointments.models import Appointment
        from datetime import time

        appointment = Appointment.objects.create(
            business=approved_business,
            service=test_service,
            customer=customer_user,
            jy=1405, jm=4, jd=22,
            time_slot=time(10, 0),
            total_price=450000,
        )

        reminder = RenewalReminder.objects.create(
            business=approved_business,
            customer=customer_user,
            appointment=appointment,
            service=test_service,
            last_service_date='1405/04/22',
            due_date='1405/05/22',
            days_remaining=30,
        )
        assert reminder.days_remaining == 30
        assert reminder.reminder_sent is False


@pytest.mark.django_db
class TestReminderTasks:
    def test_check_renewal_reminders(self, test_appointment):
        from apps.reminders.tasks import check_renewal_reminders
        test_appointment.status = 'done'
        test_appointment.save()
        result = check_renewal_reminders()
        assert 'created' in result