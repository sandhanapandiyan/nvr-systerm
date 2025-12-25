"""
Recording Models - Django ORM models for video recording management
"""

from django.db import models
from django.utils import timezone
from cameras.models import Camera
import os


class Recording(models.Model):
    """
    Recording model representing a video recording segment
    """
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='recordings', db_index=True)
    
    # File Information
    filename = models.CharField(max_length=500, unique=True, db_index=True)
    filepath = models.CharField(max_length=1000)
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    
    # Time Information
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    
    # Recording date for easy filtering
    recording_date = models.DateField(db_index=True)
    
    # Video Metadata
    resolution = models.CharField(max_length=20, blank=True, null=True)
    fps = models.IntegerField(default=0)
    codec = models.CharField(max_length=50, blank=True, null=True)
    has_audio = models.BooleanField(default=False)
    
    # Status
    is_corrupted = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'recordings'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['camera', '-start_time']),
            models.Index(fields=['camera', 'recording_date']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['recording_date']),
        ]
    
    def __str__(self):
        return f"{self.camera.name} - {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def file_exists(self):
        """Check if the recording file exists"""
        return os.path.exists(self.filepath)
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def delete_file(self):
        """Delete the recording file from disk"""
        if self.file_exists:
            try:
                os.remove(self.filepath)
                return True
            except Exception as e:
                print(f"Error deleting file {self.filepath}: {e}")
                return False
        return False
    
    def save(self, *args, **kwargs):
        """Override save to automatically set recording_date"""
        if not self.recording_date:
            self.recording_date = self.start_time.date()
        super().save(*args, **kwargs)


class ExportedVideo(models.Model):
    """
    Exported video segments model
    """
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='exports')
    
    # File Information
    filename = models.CharField(max_length=500, unique=True)
    filepath = models.CharField(max_length=1000)
    file_size = models.BigIntegerField(default=0)
    
    # Time Range
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.IntegerField(default=0)
    
    # Export Information
    format = models.CharField(max_length=10, default='mp4')
    export_date = models.DateTimeField(auto_now_add=True)
    
    # Relationships
    recordings = models.ManyToManyField(Recording, related_name='exports')
    
    class Meta:
        db_table = 'exported_videos'
        ordering = ['-export_date']
        indexes = [
            models.Index(fields=['camera', '-export_date']),
        ]
    
    def __str__(self):
        return f"Export {self.camera.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def file_exists(self):
        """Check if the export file exists"""
        return os.path.exists(self.filepath)
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def delete_file(self):
        """Delete the export file from disk"""
        if self.file_exists:
            try:
                os.remove(self.filepath)
                return True
            except Exception as e:
                print(f"Error deleting file {self.filepath}: {e}")
                return False
        return False
