"""
Camera Admin Configuration
"""

from django.contrib import admin
from .models import Camera, CameraSettings


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ['name', 'camera_type', 'status', 'is_streaming', 'is_recording', 'last_connected']
    list_filter = ['camera_type', 'status', 'is_streaming', 'is_recording']
    search_fields = ['name', 'rtsp_url']
    readonly_fields = ['created_at', 'updated_at', 'last_connected', 'last_frame_time', 'reconnect_attempts']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'camera_type', 'rtsp_url')
        }),
        ('Status', {
            'fields': ('is_streaming', 'is_recording', 'status', 'last_connected', 'last_frame_time', 'reconnect_attempts')
        }),
        ('Auto Start Settings', {
            'fields': ('auto_start_stream', 'auto_start_recording')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CameraSettings)
class CameraSettingsAdmin(admin.ModelAdmin):
    list_display = ['segment_duration', 'retention_days', 'max_storage_gb', 'enable_failsafe_monitor']
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not CameraSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False
