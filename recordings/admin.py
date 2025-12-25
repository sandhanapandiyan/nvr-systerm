"""
Recordings Admin Configuration
"""

from django.contrib import admin
from .models import Recording, ExportedVideo


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ['camera', 'start_time', 'end_time', 'duration', 'file_size_mb', 'has_audio', 'is_corrupted']
    list_filter = ['camera', 'recording_date', 'has_audio', 'is_corrupted']
    search_fields = ['camera__name', 'filename']
    readonly_fields = ['created_at', 'file_exists']
    date_hierarchy = 'recording_date'
    
    fieldsets = (
        ('Recording Information', {
            'fields': ('camera', 'filename', 'filepath')
        }),
        ('Time Information', {
            'fields': ('start_time', 'end_time', 'duration', 'recording_date')
        }),
        ('File Information', {
            'fields': ('file_size', 'file_exists')
        }),
        ('Video Metadata', {
            'fields': ('resolution', 'fps', 'codec', 'has_audio')
        }),
        ('Status', {
            'fields': ('is_corrupted', 'created_at')
        }),
    )
    
    def file_size_mb(self, obj):
        return f"{obj.file_size_mb} MB"
    file_size_mb.short_description = 'File Size'


@admin.register(ExportedVideo)
class ExportedVideoAdmin(admin.ModelAdmin):
    list_display = ['camera', 'start_time', 'end_time', 'duration', 'file_size_mb', 'export_date']
    list_filter = ['camera', 'export_date', 'format']
    search_fields = ['camera__name', 'filename']
    date_hierarchy = 'export_date'
    
    fieldsets = (
        ('Export Information', {
            'fields': ('camera', 'filename', 'filepath', 'format')
        }),
        ('Time Range', {
            'fields': ('start_time', 'end_time', 'duration')
        }),
        ('File Information', {
            'fields': ('file_size', 'export_date')
        }),
        ('Related Recordings', {
            'fields': ('recordings',),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_mb(self, obj):
        return f"{obj.file_size_mb} MB"
    file_size_mb.short_description = 'File Size'
