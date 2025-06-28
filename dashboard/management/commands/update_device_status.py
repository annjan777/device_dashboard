from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import Device
from datetime import timedelta

class Command(BaseCommand):
    help = 'Update device status to offline if no message received in last 2 minutes'

    def handle(self, *args, **options):
        # Get devices that haven't received a message in the last 2 minutes
        two_minutes_ago = timezone.now() - timedelta(minutes=2)
        devices = Device.objects.filter(
            status=True,
            last_seen__lt=two_minutes_ago
        )

        # Update their status to offline
        for device in devices:
            device.status = False
            device.save()
            self.stdout.write(
                self.style.SUCCESS(f'Set device {device.device_id} to offline')
            )
