from celery import shared_task
from django.core.management import call_command

@shared_task
def update_device_status():
    """Update device status to offline if no message received in last 2 minutes"""
    call_command('update_device_status')
