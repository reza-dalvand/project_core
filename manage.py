#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def get_settings_module():
    """
    انتخاب ماژول تنظیمات بر اساس محیط اجرا:

    اولویت:
      1. متغیر محیطی DJANGO_SETTINGS_MODULE (اگر دستی ست شده باشد)
      2. متغیر محیطی DJANGO_ENV → production / development
      3. پیش‌فرض: development
    """
    # اگر خودش دستی ست شده، دست نزن
    explicit = os.environ.get('DJANGO_SETTINGS_MODULE')
    if explicit:
        return explicit

    env = os.environ.get('DJANGO_ENV', 'development').lower()

    if env == 'production':
        return 'config.settings.production'

    return 'config.settings.development'


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', get_settings_module())
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()