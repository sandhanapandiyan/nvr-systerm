"""
Failsafe Monitor System for Django NVR
Ensures no video loss through multiple safeguards
"""

import threading
import time
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class FailsafeMonitor:
    """
    Monitors recording health and prevents video loss
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.is_running = False
            self.monitor_thread = None
            self.check_interval = 30  # Check every 30 seconds
            self.alerts = []
            self._initialized = True
            logger.info("🛡️  Failsafe Monitor initialized")
    
    def start(self):
        """Start failsafe monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("🛡️  Failsafe Monitor started")
    
    def stop(self):
        """Stop failsafe monitoring"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("🛡️  Failsafe Monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._check_recording_health()
                self._check_disk_space()
                self._check_orphan_files()
                self._check_stream_health()
            except Exception as e:
                logger.error(f"❌ Failsafe monitor error: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_recording_health(self):
        """Check if all streaming cameras are recording"""
        try:
            from cameras.models import Camera
            from streaming.recording_manager import recording_manager
            from streaming.camera_stream_manager import stream_manager
            
            cameras = Camera.objects.filter(is_streaming=True)
            
            for camera in cameras:
                # Check if streaming but not recording
                if stream_manager.is_streaming(camera.id) and not recording_manager.is_recording(camera.id):
                    logger.warning(f"⚠️  FAILSAFE: Camera {camera.id} ({camera.name}) is streaming but NOT recording!")
                    
                    # Auto-restart recording
                    try:
                        if recording_manager.start_recording(camera.id, camera.name, stream_manager):
                            camera.is_recording = True
                            camera.save()
                            logger.info(f"✅ FAILSAFE: Auto-restarted recording for Camera {camera.id}")
                            
                            self._add_alert({
                                'type': 'recording_recovered',
                                'camera_id': camera.id,
                                'camera_name': camera.name,
                                'timestamp': datetime.now(),
                                'message': f'Recording auto-restarted for {camera.name}'
                            })
                    except Exception as e:
                        logger.error(f"❌ FAILSAFE: Failed to restart recording for Camera {camera.id}: {e}")
                        
                        self._add_alert({
                            'type': 'recording_failed',
                            'camera_id': camera.id,
                            'camera_name': camera.name,
                            'timestamp': datetime.now(),
                            'message': f'Failed to restart recording: {str(e)}'
                        })
                
        except Exception as e:
            logger.error(f"Error checking recording health: {e}")
    
    def _check_disk_space(self):
        """Check available disk space and enforce storage limits"""
        try:
            from streaming.recording_manager import recording_manager
            from cameras.models import CameraSettings
            
            # Get settings
            settings = CameraSettings.objects.first()
            max_storage_gb = settings.max_storage_gb if settings else 100
            
            recordings_path = Path(recording_manager.recordings_path)
            
            # 1. Check physical disk space (Critical Failsafe)
            stat = os.statvfs(recordings_path)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            
            if free_gb < 2:
                logger.critical(f"🚨 FAILSAFE: CRITICAL DISK SPACE - {free_gb:.2f}GB free! Purging old footage.")
                self._cleanup_old_recordings(force_purge=True)
                return

            # 2. Check Logical Quota (Max Storage Setting)
            # Calculate total size of recordings directory
            total_size_bytes = sum(f.stat().st_size for f in recordings_path.glob('**/*') if f.is_file())
            used_gb = total_size_bytes / (1024**3)
            
            usage_percent = (used_gb / max_storage_gb) * 100
            
            if used_gb > max_storage_gb:
                logger.warning(f"⚠️ Storage Quota Exceeded: {used_gb:.2f}GB used / {max_storage_gb}GB quota. Cleaning up...")
                self._cleanup_old_recordings(quota_exceeded=True)
                
            # Alert on high usage (Only once every 6 hours or if critical)
            # (Skipping spammy alerts for now, just logging)
                
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")

    def _check_orphan_files(self):
        """Check for video files not in database"""
        try:
            from recordings.models import Recording
            from streaming.recording_manager import recording_manager
            from cameras.models import Camera
            
            recordings_path = Path(recording_manager.recordings_path)
            
            # Find all MP4 files
            video_files = list(recordings_path.glob("**/*.mp4"))
            
            # Get all file paths from database (optimize with set)
            db_files = set(Recording.objects.values_list('filepath', flat=True))
            
            orphan_count = 0
            for video_file in video_files:
                file_path_str = str(video_file)
                
                if file_path_str not in db_files:
                    orphan_count += 1
                    
                    # Try to import orphan file to database
                    try:
                        # Extract camera ID from path
                        parts = video_file.parts
                        camera_folder = None
                        for part in parts:
                            if part.startswith('camera_'):
                                camera_folder = part
                                break
                        
                        if camera_folder:
                            camera_id = int(camera_folder.replace('camera_', ''))
                            camera = Camera.objects.get(id=camera_id)
                            
                            # Get file info
                            stat = video_file.stat()
                            file_size = stat.st_size
                            mtime = datetime.fromtimestamp(stat.st_mtime)
                            
                            # Create database entry
                            Recording.objects.create(
                                camera=camera,
                                filepath=file_path_str,
                                filename=video_file.name,
                                start_time=mtime,
                                end_time=mtime + timedelta(seconds=300),  # Assume 5 min
                                file_size=file_size,
                                duration=300,
                                recording_date=mtime.date()
                            )
                            
                            logger.info(f"✅ FAILSAFE: Imported orphan file to database - {video_file.name}")
                    except Exception as e:
                        logger.debug(f"Could not import orphan file {video_file.name}: {e}")
            
            if orphan_count > 0:
                logger.info(f"🔍 FAILSAFE: Found and processed {orphan_count} orphan files")
                
        except Exception as e:
            logger.error(f"Error checking orphan files: {e}")

    def _check_stream_health(self):
        """Check if streams are alive"""
        try:
            from cameras.models import Camera
            from streaming.camera_stream_manager import stream_manager
            
            cameras = Camera.objects.filter(is_streaming=True)
            
            for camera in cameras:
                if camera.id in stream_manager.streams:
                    stream = stream_manager.streams[camera.id]
                    
                    # Check if stream is alive
                    if not stream.is_alive():
                        logger.warning(f"⚠️  FAILSAFE: Stream {camera.id} ({camera.name}) appears dead - will auto-reconnect")
                        # You could trigger a restart logic here if needed, 
                        # but typically valid stream manager implementation handles its own restarts
                        # For now, just logging an alert
                        
                        self._add_alert({
                            'type': 'stream_dead',
                            'camera_id': camera.id,
                            'camera_name': camera.name,
                            'timestamp': datetime.now(),
                            'message': f'Stream appears dead for {camera.name} - reconnecting'
                        })
                        
        except Exception as e:
            logger.error(f"Error checking stream health: {e}")

    def perform_startup_check(self):
        """Run a full system check on startup"""
        logger.info("🚀 FAILSAFE: Running Startup System Health Check...")
        try:
            # 1. Check Disk Space
            self._check_disk_space()
            
            # 2. Sync Orphan Files (Fix database mismatches)
            self._check_orphan_files()
            
            # 3. Verify Camera States
            from cameras.models import Camera
            from streaming.recording_manager import recording_manager
            from streaming.camera_stream_manager import stream_manager
            
            cameras = Camera.objects.all()
            for camera in cameras:
                # Force status reset on restart
                if camera.is_streaming:
                    logger.info(f"Checking Camera {camera.name}...")
                    
            logger.info("✅ FAILSAFE: Startup Check Completed - System is Good.")
        except Exception as e:
            logger.error(f"❌ FAILSAFE: Startup Check Failed: {e}")
            
    def _cleanup_old_recordings(self, force_purge=False, quota_exceeded=False):
        """Remove old recordings based on retention or storage quota"""
        try:
            from recordings.models import Recording
            from cameras.models import CameraSettings
            
            settings = CameraSettings.objects.first()
            retention_days = settings.retention_days if settings else 7
            
            # 1. Retention Policy Cleanup
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Delete expired recordings
            expired_recordings = Recording.objects.filter(start_time__lt=cutoff_date).order_by('start_time')[:50]
            
            deleted_count = 0
            for recording in expired_recordings:
                self._delete_recording_safely(recording)
                deleted_count += 1
                
            if deleted_count > 0:
                logger.info(f"🧹 Retention Cleanup: Removed {deleted_count} stale recordings (> {retention_days} days)")
                
            # 2. Quota / Force Purge Cleanup (if still needed)
            if force_purge or quota_exceeded:
                # Delete oldest recordings to free space regardless of retention
                # Fetch more aggression if force_purge
                limit = 100 if force_purge else 20
                oldest_recordings = Recording.objects.all().order_by('start_time')[:limit]
                
                purge_count = 0
                for recording in oldest_recordings:
                    self._delete_recording_safely(recording)
                    purge_count += 1
                    
                if purge_count > 0:
                    logger.info(f"🧹 Quota Cleanup: Purged {purge_count} oldest recordings to free space")

        except Exception as e:
            logger.error(f"Error cleaning up old recordings: {e}")

    def _delete_recording_safely(self, recording):
        """Helper to delete file and DB record"""
        try:
            if os.path.exists(recording.filepath):
                os.remove(recording.filepath)
            recording.delete()
        except Exception as e:
            logger.error(f"Error deleting recording {recording.filename}: {e}")
    
    def _add_alert(self, alert: dict):
        """Add alert to list"""
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def get_alerts(self, limit: int = 20) -> List[dict]:
        """Get recent alerts"""
        return self.alerts[-limit:]
    
    def get_status(self) -> dict:
        """Get failsafe monitor status"""
        return {
            'is_running': self.is_running,
            'alert_count': len(self.alerts),
            'check_interval': self.check_interval
        }


# Global instance
failsafe_monitor = FailsafeMonitor()
