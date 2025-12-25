"""
Cameras app configuration
"""
from django.apps import AppConfig


class CamerasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cameras'
    
    def ready(self):
        """Initialize failsafe monitor when app is ready"""
        # Only run in main process, not in reloader
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            from streaming.failsafe_monitor import failsafe_monitor
            # Run startup check
            failsafe_monitor.perform_startup_check()
            failsafe_monitor.start()

            # Auto-start recordings for all cameras
            from cameras.models import Camera
            from streaming.recording_manager import recording_manager
            
            try:
                cameras = Camera.objects.all()
                if cameras.exists():
                     print(f"🎥 Auto-starting recordings for {cameras.count()} cameras...")
                     for camera in cameras:
                         # We pass None for stream_manager as the new FFmpeg recorder doesn't need it
                         recording_manager.start_recording(camera.id, camera.name, None)
            except Exception as e:
                print(f"❌ Failed to auto-start recordings: {e}")
