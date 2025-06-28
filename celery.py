from celery import Celery
from django.conf import settings

app = Celery('device_dashboard')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
