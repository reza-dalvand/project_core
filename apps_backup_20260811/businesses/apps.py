from django.apps import AppConfig


class BusinessesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.businesses'
    verbose_name = '🏢 کسب‌وکارها و خدمات'

    def ready(self):
        # سیگنال‌ها فقط باید داخل ready() import شوند
        import apps.businesses.signals  # noqa