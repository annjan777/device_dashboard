from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('log/create/', views.DeviceLogCreateView.as_view(), name='create_log'),
    path('get_recent_messages/', views.get_recent_messages, name='get_recent_messages'),
    path('get_all_logs/', views.get_all_logs, name='get_all_logs'),
    path('device/<str:device_id>/logs/', views.get_all_logs, name='device_logs'),
    path('api/firmware/', views.get_firmware, name='get_firmware'),
    path('api/device/<str:device_id>/query/', views.query_device, name='query_device'),
    path('api/devices/status/', views.get_device_statuses, name='get_device_statuses'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
