from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

class Device(models.Model):
    name = models.CharField(max_length=100)
    device_id = models.CharField(
        max_length=50,
        unique=True,
        help_text='Device ID must be alphanumeric (e.g., "001", "ESP123")'
    )
    device_type = models.CharField(
        max_length=50,
        help_text='Type of device (e.g., "BMF", "ESP")'
    )
    last_seen = models.DateTimeField(null=True, blank=True)
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('idle', 'Idle'),
        ('offline', 'Offline')
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='offline'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate device_id format"""
        if not self.device_id.isalnum():
            raise ValidationError({
                'device_id': 'Device ID must be alphanumeric (letters and numbers only)'
            })
        if not self.device_id.strip():
            raise ValidationError({
                'device_id': 'Device ID cannot be empty'
            })
        
        # Ensure device_type is not empty
        if not self.device_type.strip():
            raise ValidationError({
                'device_type': 'Device Type cannot be empty'
            })

    def save(self, *args, **kwargs):
        """Clean and validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.device_type} - {self.device_id}"

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['device_id'], name='unique_device_id'),
            models.UniqueConstraint(fields=['device_type', 'device_id'], name='unique_device_type_id')
        ]

from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
import zipfile

class Firmware(models.Model):
    version = models.CharField(max_length=50)
    firmware_file = models.FileField(upload_to='firmware/versions/')
    firmware_folder = models.FileField(upload_to='firmware/folders/', null=True, blank=True)
    release_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"v{self.version}"

    def save(self, *args, **kwargs):
        # If a folder is uploaded, create a zip file from it
        if self.firmware_folder and not self.firmware_file:
            fs = FileSystemStorage()
            folder_path = fs.path(self.firmware_folder.name)
            zip_path = os.path.join(settings.MEDIA_ROOT, f'firmware/versions/v{self.version}.zip')
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
            
            # Save the zip file path to firmware_file
            self.firmware_file = fs.save(f'firmware/versions/v{self.version}.zip', open(zip_path, 'rb'))
            
            # Delete the original folder
            fs.delete(self.firmware_folder.name)
            self.firmware_folder = None
        
        super().save(*args, **kwargs)

    @property
    def file_url(self):
        """Return the full URL for the firmware file"""
        if self.firmware_file:
            return self.firmware_file.url
        return None

    class Meta:
        ordering = ['-created_at']
        unique_together = ['version']

class DeviceLog(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
