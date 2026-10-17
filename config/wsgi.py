# config/wsgi.py
"""
WSGI config for BeauClub Backend.
"""
import os


def _get_settings_module():
    explicit = os.environ.get('DJANGO_SETTINGS_MODULE')
    if explicit:
        return explicit

    env = os.environ.get('DJANGO_ENV', 'development').lower()

    if env == 'production':
        return 'config.settings.production'

    return 'config.settings.development'


os.environ.setdefault('DJANGO_SETTINGS_MODULE', _get_settings_module())

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()