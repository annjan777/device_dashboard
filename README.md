# Device Dashboard

A Django-based dashboard for monitoring IoT devices using MQTT protocol.

## Features

- Real-time device monitoring
- Device status tracking
- Log management
- MQTT integration
- Modern responsive UI

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Create superuser:
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

6. Start the MQTT broker (e.g., Mosquitto):
```bash
mosquitto -v
```

## Project Structure

```
device_dashboard/
├── dashboard/              # Django app
│   ├── models.py          # Device and log models
│   ├── views.py           # Views for dashboard and logs
│   ├── urls.py            # URL configurations
│   └── templates/          # HTML templates
│       └── dashboard/
│           ├── dashboard.html
│           ├── device_logs.html
│           └── device_log_form.html
├── device_dashboard/      # Project settings
│   ├── settings.py        # Django settings
│   └── urls.py            # Project URLs
├── manage.py              # Django management script
├── requirements.txt       # Project dependencies
└── README.md             # Project documentation
```

## Usage

1. Access the dashboard at `http://localhost:8000/`
2. Add devices through the admin panel
3. Devices will automatically update their status when sending MQTT messages
4. View logs for each device by clicking on its panel
5. Use the + button to manually create log entries

## MQTT Integration

The system uses MQTT protocol to receive real-time updates from devices. Devices should publish messages to the topic:

```
devices/<device_id>
```

The message payload should be a JSON object containing the device data.
