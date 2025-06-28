# Device Dashboard Documentation

## Project Overview
This is a Django-based device dashboard system that monitors IoT devices through MQTT protocol. It provides real-time device status updates, message logging, and firmware management.

## Key Components

### 1. Models (models.py)
```python
class Device(models.Model):
    name = models.CharField(max_length=100)
    device_id = models.CharField(max_length=50, unique=True)
    device_type = models.CharField(max_length=50)
    last_seen = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```
- Stores device information
- Each device has a unique device_id
- Tracks device status (online/offline)
- Maintains timestamps for last seen and creation

```python
class DeviceLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    data = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
```
- Stores device communication logs
- Links logs to specific devices
- Maintains timestamp for each log entry

```python
class Firmware(models.Model):
    version = models.CharField(max_length=20)
    release_notes = models.TextField()
    firmware_file = models.FileField(upload_to='firmware/versions/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```
- Manages firmware versions
- Stores firmware files
- Tracks active/inactive firmware versions

### 2. Views (views.py)
```python
def connect_mqtt():
```
- Handles MQTT connection and message handling
- Subscribes to "devices/#" topic
- Processes incoming messages
- Updates device status and logs

```python
def update_device_status():
```
- Background task to update device status
- Checks devices that haven't communicated in 2 minutes
- Sets their status to offline

```python
class DashboardView(ListView):
```
- Main dashboard view
- Shows all devices
- Displays recent logs
- Shows online/offline status

```python
def get_firmware(request):
```
- API endpoint for firmware information
- Returns firmware details in specified format

### 3. Admin (admin.py)
```python
class DeviceAdmin(admin.ModelAdmin):
```
- Custom admin interface for Device model
- Allows device management
- Shows device logs

```python
class FirmwareAdmin(admin.ModelAdmin):
```
- Custom admin interface for Firmware model
- Manages firmware versions
- Handles firmware file uploads

### 4. URLs (urls.py)
```python
urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('log/create/', DeviceLogCreateView.as_view(), name='create_log'),
    path('get_recent_messages/', get_recent_messages, name='get_recent_messages'),
    path('get_all_logs/', get_all_logs, name='get_all_logs'),
    path('device/<str:device_id>/logs/', get_all_logs, name='device_logs'),
    path('api/firmware/', get_firmware, name='get_firmware'),
]
```
- Defines all application routes
- API endpoints
- Dashboard views
- Log management

### 5. Templates (dashboard.html)
- Main dashboard template
- Shows device status
- Displays recent logs
- Provides device controls
- Shows firmware information

## Key Features

### Device Management
- Real-time device status updates
- Device type tracking
- Last seen timestamp
- Online/offline status
- Device logs

### MQTT Integration
- Real-time message handling
- Device discovery
- Message logging
- Status updates

### Firmware Management
- Firmware version control
- Active/inactive firmware
- Release notes
- File management

### Dashboard Features
- Device overview
- Recent logs
- Online/offline status
- Device controls
- Firmware information

## Configuration

### Settings (settings.py)
```python
MQTT_BROKER_HOST = 'localhost'
MQTT_BROKER_PORT = 1883
ALLOWED_HOSTS = []
TIME_ZONE = 'Asia/Kolkata'
```
- MQTT broker configuration
- Server settings
- Time zone configuration

## Usage

### Device Status
1. Devices are marked online when they send a message
2. Devices are marked offline if they haven't sent a message in 2 minutes
3. Status is updated every minute by background task

### Message Logging
1. All device messages are logged
2. Logs are stored with timestamps
3. Recent logs are displayed on dashboard
4. Logs can be viewed per device

### Firmware
1. Firmware can be uploaded through admin interface
2. Multiple versions can be maintained
3. Active version is served to devices
4. Release notes are tracked

## Error Handling
- MQTT connection errors
- Device ID validation
- Log entry duplicates
- Firmware upload validation
- Timezone handling

## Security
- Device ID validation
- Message format validation
- Admin interface protection
- File upload validation

## Future Enhancements
1. Device grouping
2. Advanced filtering
3. Alert system
4. Historical data analysis
5. Device metrics
6. Batch operations

## Troubleshooting
1. Check MQTT broker connection
2. Verify device ID format
3. Check message format
4. Review logs for errors
5. Verify permissions

## Contact
For any issues or enhancements, please contact the development team.
