from django.contrib import admin
from .models import Device, DeviceLog, Firmware

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_id', 'status', 'last_seen', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('name', 'device_id')
    ordering = ('-updated_at',)

@admin.register(Firmware)
class FirmwareAdmin(admin.ModelAdmin):
    list_display = ('version', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('version', 'release_notes')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('version', 'is_active', 'release_notes')
        }),
        ('Firmware Files', {
            'fields': ('firmware_file', 'firmware_folder')
        }),
    )

    def save_model(self, request, obj, form, change):
        # If a folder was uploaded, create a zip file from it
        if obj.firmware_folder and not obj.firmware_file:
            fs = FileSystemStorage()
            folder_path = fs.path(obj.firmware_folder.name)
            zip_path = os.path.join(settings.MEDIA_ROOT, 'firmware/versions', f'v{obj.version}.zip')
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
            
            # Save the zip file path to firmware_file
            obj.firmware_file = fs.save(f'firmware/versions/v{obj.version}.zip', open(zip_path, 'rb'))
            
            # Delete the original folder
            fs.delete(obj.firmware_folder.name)
            obj.firmware_folder = None
        
        super().save_model(request, obj, form, change)

@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ('device', 'timestamp', 'created_at')
    list_filter = ('device', 'timestamp')
    search_fields = ('device__name', 'device__device_id')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'created_at')

admin.site.site_header = 'Device Dashboard'
admin.site.site_title = 'Device Dashboard'
admin.site.index_title = 'Device Management'

# Removed the incorrect @admin.register(firmware) line
# Firmware model is already registered above