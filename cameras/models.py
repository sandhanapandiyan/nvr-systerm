"""
Camera Models - Django ORM models for camera management
Optimized with proper indexing and validation
"""

from django.db import models
from django.core.validators import URLValidator
from django.utils import timezone


class Camera(models.Model):
    """
    Camera model representing an RTSP/ONVIF camera
    """
    CAMERA_TYPES = [
        ('RTSP', 'RTSP Stream'),
        ('ONVIF', 'ONVIF Camera'),
        ('HTTP', 'HTTP Stream'),
    ]
    
    STATUS_CHOICES = [
        ('offline', 'Offline'),
        ('online', 'Online'),
        ('error', 'Error'),
        ('connecting', 'Connecting'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=200, db_index=True)
    camera_type = models.CharField(max_length=10, choices=CAMERA_TYPES, default='RTSP')
    
    # Connection Details - Separate fields for easier management
    username = models.CharField(max_length=100, blank=True, help_text="Camera username")
    password = models.CharField(max_length=100, blank=True, help_text="Camera password")
    ip_address = models.CharField(max_length=100, blank=True, help_text="Camera IP address or hostname")
    port = models.IntegerField(default=554, help_text="RTSP port (usually 554)")
    stream_path = models.CharField(max_length=200, blank=True, help_text="Stream path (e.g., /cam/realmonitor?channel=1&subtype=0)")
    
    # Full RTSP URL (can be auto-generated from above fields or set manually)
    rtsp_url = models.CharField(max_length=500, blank=True)
    
    # State
    is_streaming = models.BooleanField(default=False, db_index=True)
    is_recording = models.BooleanField(default=False, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', db_index=True)
    
    # Connection Stats
    last_connected = models.DateTimeField(null=True, blank=True)
    last_frame_time = models.DateTimeField(null=True, blank=True)
    reconnect_attempts = models.IntegerField(default=0)
    
    # Settings
    auto_start_stream = models.BooleanField(default=True)
    auto_start_recording = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cameras'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_streaming', 'is_recording']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.camera_type})"
    
    def mark_online(self):
        """Mark camera as online and update last connected time"""
        self.status = 'online'
        self.last_connected = timezone.now()
        self.last_frame_time = timezone.now()
        self.reconnect_attempts = 0
        self.save(update_fields=['status', 'last_connected', 'last_frame_time', 'reconnect_attempts'])
    
    def mark_offline(self):
        """Mark camera as offline"""
        self.status = 'offline'
        self.save(update_fields=['status'])
    
    def update_frame_time(self):
        """Update last frame received time"""
        self.last_frame_time = timezone.now()
        self.save(update_fields=['last_frame_time'])
    
    def increment_reconnect_attempts(self):
        """Increment reconnection attempts"""
        self.reconnect_attempts += 1
        self.save(update_fields=['reconnect_attempts'])
    
    def build_rtsp_url(self):
        """Build RTSP URL from separate credential fields"""
        from urllib.parse import quote
        
        if not self.ip_address:
            return self.rtsp_url  # Return existing URL if no IP provided
        
        # Build auth part
        if self.username:
            auth = f"{quote(self.username, safe='')}"
            if self.password:
                auth += f":{quote(self.password, safe='')}"
            auth += "@"
        else:
            auth = ""
        
        # Build URL
        port_str = f":{self.port}" if self.port and self.port != 554 else ":554"
        path = self.stream_path if self.stream_path else "/"
        if not path.startswith('/'):
            path = '/' + path
        
        url = f"rtsp://{auth}{self.ip_address}{port_str}{path}"
        return url
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate RTSP URL if needed"""
        # If IP is provided but no full URL, build it
        if self.ip_address and not self.rtsp_url:
            self.rtsp_url = self.build_rtsp_url()
        # If separate fields are empty but URL exists, keep the URL
        super().save(*args, **kwargs)


class CameraSettings(models.Model):
    """
    Global camera settings
    """
    # Recording Settings
    segment_duration = models.IntegerField(default=300, help_text="Recording segment duration in seconds")
    retention_days = models.IntegerField(default=7, help_text="Days to keep recordings")
    
    # Video Settings
    video_format = models.CharField(max_length=10, default='mp4', help_text="Recording video format (mp4, mkv, mov, avi, ts)")
    video_codec = models.CharField(max_length=20, default='copy', help_text="Video codec (copy, libx264, etc.)")
    
    # Audio Settings
    audio_codec = models.CharField(max_length=20, default='aac', help_text="Audio codec (aac, mp3, copy, an)")
    audio_bitrate = models.CharField(max_length=10, default='128k', help_text="Audio bitrate (64k, 128k, 256k)")
    
    # Streaming Settings
    stream_timeout = models.IntegerField(default=10, help_text="Stream timeout in seconds")
    max_reconnect_attempts = models.IntegerField(default=5)
    reconnect_delay = models.IntegerField(default=5, help_text="Delay between reconnection attempts in seconds")
    
    # Storage Settings
    max_storage_gb = models.IntegerField(default=100, help_text="Maximum storage in GB")
    
    # System Settings
    enable_failsafe_monitor = models.BooleanField(default=True)
    
    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'camera_settings'
        verbose_name = 'Camera Settings'
        verbose_name_plural = 'Camera Settings'
    
    def __str__(self):
        return "Camera Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create settings singleton"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
