# apps/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = '👤 احراز هویت و کاربران'

    def ready(self):
        import apps.accounts.signals  # noqa