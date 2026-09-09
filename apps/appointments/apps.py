from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.appointments'
    verbose_name = '📅 نوبت‌ها'

    def ready(self):
        """ثبت تسک‌های سلری هنگام شروع Django"""
        try:
            import apps.appointments.tasks  # noqa: F401
        except ImportError:
            pass