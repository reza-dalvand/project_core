from django.apps import AppConfig


class AdvancedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.advanced'
    verbose_name = '🚀 ویژگی‌های پیشرفته'

    def ready(self):
        import apps.advanced.signals  # noqa