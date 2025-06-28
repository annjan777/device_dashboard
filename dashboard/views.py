from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from .models import Device, DeviceLog, Firmware

import json
import threading
import paho.mqtt.client as mqtt
from datetime import timedelta
import time

# Global variable for storing recent messages in memory
# Keep only the last 10 messages to avoid memory issues
recent_messages = []
MAX_RECENT_MESSAGES = 10

# MQTT Client setup
mqtt_client_instance = None

# Function to update device status
def update_device_status():
    """Update device status based on last seen time"""
    now = timezone.now()
    two_minutes_ago = now - timedelta(minutes=2)
    five_minutes_ago = now - timedelta(minutes=5)
    
    # Update devices that were online but haven't been seen in 2 minutes to idle
    idle_devices = Device.objects.filter(
        status='online',
        last_seen__lt=two_minutes_ago
    )
    
    for device in idle_devices:
        device.status = 'idle'
        device.save()
        print(f" Set device {device.device_id} to idle")
    
    # Update devices that were idle but haven't been seen in 5 minutes to offline
    offline_devices = Device.objects.filter(
        status='idle',
        last_seen__lt=five_minutes_ago
    )
    
    for device in offline_devices:
        device.status = 'offline'
        device.save()
        print(f" Set device {device.device_id} to offline")

# Start periodic status update
def start_status_update():
    """Start a background thread to update device status every minute"""
    def run_periodic():
        while True:
            update_device_status()
            time.sleep(60)  # Check every minute
    
    thread = threading.Thread(target=run_periodic, daemon=True)
    thread.start()

def send_mqtt_message(topic, message):
    """Send an MQTT message"""
    if mqtt_client_instance and mqtt_client_instance.is_connected():
        try:
            result = mqtt_client_instance.publish(topic, json.dumps(message))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✅ Message sent to {topic}: {message}")
                return True
            else:
                print(f"❌ Failed to send message: {result.rc}")
                return False
        except Exception as e:
            print(f"❌ Error sending MQTT message: {str(e)}")
            return False
    else:
        print("❌ MQTT client not connected")
        return False

def query_device_status(device_id):
    """Send a ping message to query device status"""
    topic = "check"
    message = {
        "device-id": device_id,
        "message": "ping"
    }
    return send_mqtt_message(topic, message)

def connect_mqtt():
    global mqtt_client_instance

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ Successfully connected to MQTT Broker")
            # Subscribe to all device messages
            client.subscribe("devices/#")
            # Also subscribe to the check topic for query responses
            client.subscribe("check/response")
        else:
            print(f"❌ MQTT Connection failed with code {rc}")

    def on_message(client, userdata, msg):
        try:
            print(f"\n📩 MQTT Message Received on topic: {msg.topic}")
            
            # Skip processing if payload is empty
            if not msg.payload:
                print("⚠️ Empty payload received, skipping...")
                return
                
            print(f"📦 Raw Payload: {msg.payload}")

            try:
                # Decode JSON message
                message_data = json.loads(msg.payload.decode())
                print(f"✅ Decoded JSON: {message_data}")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to decode JSON: {e}")
                return

            # Extract device type from topic or message
            device_type = "unknown"
            if 'devices/' in msg.topic:
                device_type = msg.topic.split('/')[-1]
            print(f"🎯 Device Type: {device_type}")

            # Extract and validate device-id
            device_id = message_data.get('device-id')
            if not device_id:
                print("❌ device-id is missing in payload!")
                return
            
            device_id = str(device_id).strip()
            if not device_id or not device_id.isalnum():
                print(f"❌ Invalid device-id format: {device_id}")
                return

            message_content = str(message_data.get('message', '')).lower().strip()
            print(f"🎯 Message Content: {message_content}")

            # Initialize variables
            created = False
            device = None
            
            # Check if device already exists with this device_id
            try:
                existing_device = Device.objects.filter(device_id=device_id).first()
                if existing_device:
                    print(f"🔄 Found existing device: {existing_device}")
                    # Update existing device
                    existing_device.device_type = device_type
                    
                    # Update status based on message content
                    if message_content == 'idle':
                        existing_device.status = 'idle'
                    elif message_content == 'online':
                        existing_device.status = 'online'
                    else:
                        # For any other message, consider it as online
                        existing_device.status = 'online'
                        
                    existing_device.last_seen = timezone.now()
                    existing_device.save()
                    print(f"✅ Updated device {device_id} status to {existing_device.status}")
                    device = existing_device
                else:
                    # Create new device
                    device = Device.objects.create(
                        device_id=device_id,
                        device_type=device_type,
                        status='online',
                        last_seen=timezone.now(),
                        name=f"{device_type} - {device_id}"
                    )
                    created = True
                    print(f"✅ New device created: {device_id}")
            except Exception as e:
                print(f"❌ Error updating/creating device status: {e}")
                return

            # Create or update device log
            log_entry, log_created = DeviceLog.objects.get_or_create(
                device=device,
                data=message_content,
                defaults={'timestamp': timezone.now()}
            )
            
            if log_created:
                print(f"📝 Log entry created for {device_id}: {message_content}")
            else:
                print(f"🔄 Log entry already exists for {device_id}: {message_content}")

            # Only store logs for messages from devices/ topics
            if msg.topic.startswith('devices/'):
                # Extract device type from topic (devices/type/device_id)
                topic_parts = msg.topic.split('/')
                if len(topic_parts) >= 3:  # Ensure we have at least devices/type/id
                    device_type = topic_parts[1]  # Get the type part
                    
                    # Save to in-memory recent messages (keep only last 10)
                    message = {
                        'device_id': device_id,
                        'data': message_content,
                        'timestamp': timezone.now().isoformat(),
                        'log_id': log_entry.id,
                        'device_type': device_type
                    }
                    
                    # Check if this message already exists (same device and data)
                    existing_index = None
                    for i, msg in enumerate(recent_messages):
                        if msg['device_id'] == device_id and msg['data'] == message_content:
                            existing_index = i
                            break
                    
                    if existing_index is not None:
                        # Update existing message timestamp
                        recent_messages[existing_index]['timestamp'] = message['timestamp']
                    else:
                        # Ensure we don't exceed max messages
                        if len(recent_messages) >= MAX_RECENT_MESSAGES:
                            recent_messages.pop(0)  # Remove oldest message
                        # Add new message
                        recent_messages.append(message)
                
            # Keep only the last MAX_RECENT_MESSAGES messages
            if len(recent_messages) > MAX_RECENT_MESSAGES:
                recent_messages = recent_messages[-MAX_RECENT_MESSAGES:]
                
            # Check if device exists and update/create if needed
            try:
                existing_device = Device.objects.filter(device_id=device_id).first()
                if existing_device:
                    print(f"🔄 Found existing device: {existing_device}")
                    # Update existing device
                    existing_device.device_type = device_type
                    
                    # Update status based on message content
                    if message_content == 'idle':
                        existing_device.status = 'idle'
                    elif message_content == 'online':
                        existing_device.status = 'online'
                    else:
                        # For any other message, consider it as online
                        existing_device.status = 'online'
                        
                    existing_device.last_seen = timezone.now()
                    existing_device.save()
                    print(f"✅ Updated device {device_id} status to {existing_device.status}")
                    device = existing_device
                else:
                    # Create new device
                    device = Device.objects.create(
                        device_id=device_id,
                        device_type=device_type,
                        status='online',
                        last_seen=timezone.now(),
                        name=f"{device_type} - {device_id}"
                    )
                    print(f"✅ New device created: {device_id}")

                # Create or update device log
                log_entry, log_created = DeviceLog.objects.get_or_create(
                    device=device,
                    data=message_content,
                    defaults={'timestamp': timezone.now()}
                )
                
                if log_created:
                    print(f"📝 Log entry created for {device_id}: {message_content}")
                else:
                    print(f"🔄 Log entry already exists for {device_id}: {message_content}")
                
                # Check if this message already exists (same device and data)
                existing_index = None
                for i, msg in enumerate(recent_messages):
                    if msg['device_id'] == device_id and msg['data'] == message_content:
                        existing_index = i
                        break
                
                if existing_index is not None:
                    # Update existing message timestamp
                    recent_messages[existing_index]['timestamp'] = message['timestamp']
                else:
                    # Add new message
                    recent_messages.append(message)
                    
                # Keep only the last MAX_RECENT_MESSAGES messages
                if len(recent_messages) > MAX_RECENT_MESSAGES:
                    recent_messages = recent_messages[-MAX_RECENT_MESSAGES:]

            except Exception as e:
                print(f"❌ Error processing message: {e}")

        except Exception as e:
            print(f"❌ Error in on_message: {e}")


    # Create MQTT client instance if it doesn't exist
    if mqtt_client_instance is None:
        try:
            client_id = f"dashboard_{int(time.time())}"
            mqtt_client_instance = mqtt.Client(client_id=client_id)
            mqtt_client_instance.on_connect = on_connect
            mqtt_client_instance.on_message = on_message
            
            # Set last will and testament
            mqtt_client_instance.will_set("dashboard/status", "offline", qos=1, retain=True)
            
            from django.conf import settings
            print(f"🔌 Connecting to MQTT broker at {getattr(settings, 'MQTT_BROKER_HOST', 'localhost')}:{getattr(settings, 'MQTT_BROKER_PORT', 1883)}...")
            mqtt_client_instance.connect(
                getattr(settings, 'MQTT_BROKER_HOST', 'localhost'),
                getattr(settings, 'MQTT_BROKER_PORT', 1883),
                60
            )
            mqtt_client_instance.loop_start()
            
            # Publish online status
            mqtt_client_instance.publish("dashboard/status", "online", qos=1, retain=True)
            
        except Exception as e:
            print(f"❌ Failed to connect to MQTT broker: {e}")
            mqtt_client_instance = None
    else:
        # If client exists but not connected, try to reconnect
        if not mqtt_client_instance.is_connected():
            try:
                mqtt_client_instance.reconnect()
                mqtt_client_instance.loop_start()
            except Exception as e:
                print(f"❌ Failed to reconnect to MQTT broker: {e}")
                mqtt_client_instance = None

# Start MQTT client in background thread
threading.Thread(target=connect_mqtt, daemon=True).start()

# Start status update thread
start_status_update()

# ========== Views ==========

@csrf_exempt
def get_recent_messages(request):
    return JsonResponse({'messages': recent_messages})


@login_required
def get_all_logs(request, device_id=None):
    if request.is_ajax():
        if device_id:
            logs = DeviceLog.objects.filter(device__device_id=device_id).order_by('-timestamp')
        else:
            device_id = request.GET.get('device_id')
            if not device_id:
                return JsonResponse({'error': 'Device ID required'}, status=400)
            logs = DeviceLog.objects.filter(device__device_id=device_id).order_by('-timestamp')

        return JsonResponse({
            'logs': [
                {
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'data': log.data
                }
                for log in logs
            ]
        })

    if not device_id:
        return JsonResponse({'error': 'Device ID required'}, status=400)

    device = Device.objects.get(device_id=device_id)
    logs = DeviceLog.objects.filter(device=device).order_by('-timestamp')
    return render(request, 'dashboard/device_logs.html', {
        'device': device,
        'logs': logs
    })


class DashboardView(ListView):
    model = Device
    template_name = 'dashboard/dashboard.html'
    context_object_name = 'devices'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_logs'] = DeviceLog.objects.all().order_by('-timestamp')
        context['online_devices'] = Device.objects.filter(status=True)
        context['offline_devices'] = Device.objects.filter(status=False)
        context['recent_messages'] = recent_messages
        return context


class DeviceLogCreateView(CreateView):
    model = DeviceLog
    fields = ['device', 'data']
    template_name = 'dashboard/device_log_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        form.instance.timestamp = timezone.now()
        messages.success(self.request, 'Log entry created successfully')
        return super().form_valid(form)


def device_logs(request, device_id):
    device = Device.objects.get(device_id=device_id)
    logs = DeviceLog.objects.filter(device=device).order_by('-timestamp')
    return render(request, 'dashboard/device_logs.html', {
        'device': device,
        'logs': logs
    })


@csrf_protect
@require_http_methods(["POST"])
def query_device(request, device_id):
    """Handle device query request"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=403)
    
    device = get_object_or_404(Device, device_id=device_id)
    
    # Send ping message to device
    success = query_device_status(device_id)
    
    if success:
        # Set status to 'idle' immediately to show we're waiting for response
        device.status = 'idle'
        device.save()
        return JsonResponse({'status': 'success', 'message': 'Query sent to device'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Failed to send query'}, status=500)


@login_required
def get_device_statuses(request):
    """API endpoint to get status of all devices"""
    print("\n=== get_device_statuses called ===")
    print(f"User: {request.user}")
    print(f"Authenticated: {request.user.is_authenticated}")
    
    try:
        devices = list(Device.objects.all())
        print(f"Found {len(devices)} devices in database")
        
        device_data = []
        for device in devices:
            status = device.status or 'offline'
            print(f"Device: {device.device_id}, Status: {status}, Last Seen: {device.last_seen}")
            
            device_data.append({
                'device_id': device.device_id,
                'status': status,
                'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                'name': device.name
            })
        
        response_data = {'devices': device_data}
        print("Returning device data:", response_data)
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Error in get_device_statuses: {str(e)}")
        return JsonResponse(
            {'error': str(e), 'success': False},
            status=500
        )


def get_firmware(request):
    try:
        firmware = Firmware.objects.filter(is_active=True).order_by('-created_at').first()
        if firmware:
            response = {
                'type': 'my-device-type',
                'version': firmware.version,
                'url': f"{request.scheme}://{request.get_host()}{firmware.firmware_file.url}"
            }
            return JsonResponse(response)
        else:
            return JsonResponse({
                'error': 'No active firmware found',
                'success': False
            }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)
