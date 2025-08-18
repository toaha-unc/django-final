"""
WSGI config for freelancer_platform project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Use production settings for Vercel deployment
if os.environ.get('VERCEL_ENV') == 'production':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freelancer_platform.settings_production')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freelancer_platform.settings')

application = get_wsgi_application()
