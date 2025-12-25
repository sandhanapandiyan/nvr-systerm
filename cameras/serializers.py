"""
Camera Serializers for Django REST Framework
"""

from rest_framework import serializers
from .models import Camera, CameraSettings


class CameraSerializer(serializers.ModelSerializer):
    """Serializer for Camera model"""
    
    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'camera_type', 'rtsp_url', 
            'is_streaming', 'is_recording', 'status',
            'last_connected', 'last_frame_time', 'reconnect_attempts',
            'auto_start_stream', 'auto_start_recording',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_streaming', 'is_recording', 'status',
            'last_connected', 'last_frame_time', 'reconnect_attempts',
            'created_at', 'updated_at'
        ]


class CameraListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for camera list"""
    
    class Meta:
        model = Camera
        fields = ['id', 'name', 'camera_type', 'is_streaming', 'is_recording', 'status']


class CameraSettingsSerializer(serializers.ModelSerializer):
    """Serializer for Camera Settings"""
    
    class Meta:
        model = CameraSettings
        fields = '__all__'
