"""
确保 django-celery-beat DatabaseScheduler برای یادآوری‌های تمدید رکورد PeriodicTask داشته باشد.

✅ دلیل نیاز:
وقتی از DatabaseScheduler استفاده می‌کنید، CELERY_BEAT_SCHEDULE به‌تنهایی کافی نیست
و باید رکورد در جدول django_celery_beat_periodictask وجود داشته باشد.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "ایجاد یا بروزرسانی PeriodicTask برای check_renewal_reminders"

    TASK_NAME = "check-renewal-reminders"
    TASK_PATH = "apps.reminders.tasks.check_renewal_reminders"

    def handle(self, *args, **options):
        tz = dj_timezone.get_default_timezone()

        schedule, schedule_created = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="8",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone=tz,
        )

        periodic_task, task_created = PeriodicTask.objects.update_or_create(
            name=self.TASK_NAME,
            defaults={
                "task": self.TASK_PATH,
                "crontab": schedule,
                "interval": None,
                "solar": None,
                "enabled": True,
                "one_off": False,
                "args": "",
                "kwargs": "",
            },
        )

        if schedule_created:
            self.stdout.write(
                self.style.SUCCESS("✅ CrontabSchedule created for reminder task.")
            )
        else:
            self.stdout.write("ℹ️ CrontabSchedule already existed.")

        if task_created:
            self.stdout.write(
                self.style.SUCCESS("✅ PeriodicTask created for reminder task.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ PeriodicTask updated for reminder task.")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Task: {periodic_task.task} | Enabled: {periodic_task.enabled}"
            )
        )