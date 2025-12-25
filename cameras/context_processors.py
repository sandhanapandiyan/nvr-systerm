"""
Context processors for Django NVR
Makes global data available to all templates
"""
from cameras.models import Camera
from streaming.camera_stream_manager import stream_manager


def camera_context(request):
    """Add camera counts to all template contexts"""
    total_cameras = Camera.objects.count()
    active_cameras = stream_manager.get_active_count()
    
    return {
        'total_cameras': total_cameras,
        'active_cameras_count': active_cameras,
    }
