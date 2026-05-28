import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control.settings')

app = Celery('nutrihelp')

# Namespace 'CELERY' — todas as configs no settings.py prefixadas com CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover encontra tasks.py em todos os apps em INSTALLED_APPS
app.autodiscover_tasks()
