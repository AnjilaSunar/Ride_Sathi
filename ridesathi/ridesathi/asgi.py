"""
ASGI config for ridesathi project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""
import pymysql
pymysql.install_as_MySQLdb()

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ridesathi.settings')

application = get_asgi_application()
