"""
Recording Manager for Django NVR
Handles continuous recording of camera streams to video files
"""

import cv2
import os
import threading
import time
import logging
import subprocess
import shlex
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CameraRecorder:
    """Manages recording for a single camera"""
    
    def __init__(self, camera_id: int, camera_name: str, recordings_path: str):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.recordings_path = recordings_path
        self.is_recording = False
        self.thread = None
        self.current_writer = None
        self.current_segment_start = None
        self.current_segment_path = None  # Track current segment path
        self.frames_written = 0
        
        # Get settings from database
        self._load_settings()
        
        # Create camera recording directory
        self.camera_dir = Path(self.recordings_path) / f"camera_{camera_id}"
        self.camera_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_settings(self):
        """Load camera settings from database"""
        try:
            from cameras.models import CameraSettings
            # Load global settings (first entry)
            settings = CameraSettings.objects.first()
            
            if settings:
                # Segment duration is already in seconds in DB
                self.segment_duration = settings.segment_duration
                self.fps = getattr(settings, 'recording_fps', 20)
                self.quality = getattr(settings, 'recording_quality', 'medium')
                self.video_format = getattr(settings, 'video_format', 'mp4')
                self.video_codec = getattr(settings, 'video_codec', 'copy')
                self.audio_codec = getattr(settings, 'audio_codec', 'aac')
                self.audio_bitrate = getattr(settings, 'audio_bitrate', '128k')
            else:
                # Default values if no settings found
                self.segment_duration = 300  # 5 minutes
                self.fps = 20
                self.quality = 'medium'
                self.video_format = 'mp4'
                self.video_codec = 'copy'
                self.audio_codec = 'aac'
                
        except Exception as e:
            logger.warning(f"Failed to load settings for camera {self.camera_id}: {e}")
            # Fallback to defaults
            self.segment_duration = 300
            self.fps = 20
            self.quality = 'medium'
        
    def _start_ffmpeg_process(self):
        """Internal method to launch FFmpeg process"""
        try:
            from cameras.models import Camera
            camera = Camera.objects.get(id=self.camera_id)
            rtsp_url = camera.rtsp_url
            
            # Construct FFmpeg command
            segment_list = self.camera_dir / "segments.csv"
            output_pattern = self.camera_dir / f"{self.camera_name}_%Y-%m-%d_%H-%M-%S.{self.video_format}"
            
            audio_opt = []
            if self.audio_codec == 'an':
                audio_opt = ['-an']
            elif self.audio_codec == 'copy':
                audio_opt = ['-c:a', 'copy']
            else:
                audio_opt = ['-c:a', self.audio_codec, '-b:a', self.audio_bitrate]

            cmd = [
                'ffmpeg', '-y',
                '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-c:v', self.video_codec,
            ] + audio_opt + [
                '-f', 'segment',
                '-segment_time', str(self.segment_duration),
                '-segment_format', self.video_format,
                '-segment_list', str(segment_list),
                '-segment_list_type', 'csv',
                '-reset_timestamps', '1',
                '-strftime', '1',
                # SAFETY FLAGS FOR CRASH PROTECTION
                '-movflags', '+faststart+frag_keyframe+empty_moov', # Ensure index is at start & fragmented
                '-flush_packets', '1', # Write packets to disk immediately
                str(output_pattern)
            ]
            
            logger.info(f"⚙️ Active Recording Config for Camera {self.camera_id}: "
                        f"Video={self.video_codec}, Audio={self.audio_codec}/{self.audio_bitrate}, "
                        f"Format={self.video_format}, SegDuration={self.segment_duration}s")
            
            logger.info(f"🚀 Starting FFmpeg for Camera {self.camera_id}: {' '.join(cmd)}")
            self.process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}")
            return False
        
    def start(self, stream_manager):
        """Start recording using FFmpeg subprocess"""
        if self.is_recording:
            return
            
        # Refresk settings before starting
        self._load_settings()
        
        self.is_recording = True
        
        if self._start_ffmpeg_process():
            # Start monitor thread
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            
            logger.info(f"📹 Started recording for Camera {self.camera_id}")
        else:
            self.is_recording = False
        
    def stop(self):
        """Stop recording"""
        self.is_recording = False
        
        if hasattr(self, 'process') and self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

        logger.info(f"⏹️  Stopped recording for Camera {self.camera_id}")
    
    def get_progress(self) -> dict:
        """Get current recording segment progress"""
        if not self.is_recording or self.current_segment_start is None:
            return {
                'progress': 0,
                'elapsed': 0,
                'total': self.segment_duration,
                'frames': 0
            }
        
        elapsed = (datetime.now() - self.current_segment_start).seconds
        progress = min(int((elapsed / self.segment_duration) * 100), 100)
        
        return {
            'progress': progress,
            'elapsed': elapsed,
            'total': self.segment_duration,
            'frames': self.frames_written
        }
        
        
    def _is_file_in_db(self, filename) -> bool:
        """Check if filename already exists in database"""
        try:
             from recordings.models import Recording
             return Recording.objects.filter(filename=filename).exists()
        except Exception:
             return False

    def _save_recording_db(self, filename, start_time_str, end_time_str):
        """Save recording segment to database"""
        try:
            from cameras.models import Camera
            from recordings.models import Recording
            
            camera = Camera.objects.get(id=self.camera_id)
            filepath = self.camera_dir / filename
            
            # Parse start time from filename pattern: Name_YYYY-mm-dd_HH-MM-SS.mp4
            import re
            match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
            if match:
                dt_str = match.group(1)
                start_time = datetime.strptime(dt_str, "%Y-%m-%d_%H-%M-%S")
            else:
                start_time = datetime.now() # Fallback

            # Calculate duration from CSV timestamps
            try:
                start_ts = float(start_time_str)
                end_ts = float(end_time_str)
                duration = end_ts - start_ts
            except:
                duration = self.segment_duration

            end_time = start_time + timedelta(seconds=duration)
            
            file_size = filepath.stat().st_size if filepath.exists() else 0
            
            Recording.objects.create(
                camera=camera,
                filepath=str(filepath),
                filename=filename,
                start_time=start_time,
                end_time=end_time,
                file_size=file_size,
                duration=int(duration),
                recording_date=start_time.date()
            )
            logger.info(f"💾 Saved segment {filename} to DB")
            
        except Exception as e:
            logger.error(f"Failed to save to DB: {e}")

    def _monitor_loop(self):
        """Monitor segments csv for completed files and ensure continuous recording"""
        segment_list = self.camera_dir / "segments.csv"
        processed_files = set()
        
        logger.info(f"🔴 Monitor loop started for Camera {self.camera_id}")
        
        while self.is_recording:
            # Check process status and restart if needed
            if not self.process or self.process.poll() is not None:
                if self.process:
                    logger.error(f"⚠️ FFmpeg process died! Exit code: {self.process.returncode}")
                else:
                    logger.warning("⚠️ FFmpeg process missing")
                
                # Check if we should still be recording
                if self.is_recording:
                    logger.info("♻️ Auto-restarting recording process (Never Stop Mode)...")
                    time.sleep(2)  # Delay before restart
                    self._start_ffmpeg_process()
            
            if not segment_list.exists():
                time.sleep(1)
                continue
                
            try:
                import csv
                # Open with standard file handling
                with open(segment_list, 'r') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if not row: continue
                        filename = row[0]
                        if filename not in processed_files:
                            # Add to DB
                            # Row: filename, start_time, end_time
                            if len(row) >= 3:
                                # Check if file already exists in DB to prevent UNIQUE constraint error
                                if filename not in processed_files:
                                    # Just to be safe, query DB for filename existence
                                    if not self._is_file_in_db(filename):
                                        self._save_recording_db(filename, row[1], row[2])
                                    processed_files.add(filename)
                                self.current_segment_start = datetime.now()
            except Exception as e:
                pass # CSV reading error (race condition)
                
            time.sleep(2)


class RecordingManager:
    """Manages recording for all cameras"""
    
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
            self.recorders: Dict[int, CameraRecorder] = {}
            # Save to Desktop for easy access
            self.recordings_path = str(Path.home() / "Desktop" / "NVR_Recordings")
            Path(self.recordings_path).mkdir(parents=True, exist_ok=True)
            
            # Register signal handlers for graceful shutdown check
            import signal
            import atexit
            atexit.register(self.stop_all_recordings)
            
            self._initialized = True
            logger.info(f"🎥 RecordingManager initialized. Storage: {self.recordings_path}")
    
    def stop_all_recordings(self):
        """Stop all recordings gracefully"""
        logger.info("🛑 Stopping All Search Recordings gracefully...")
        for cam_id in list(self.recorders.keys()):
            self.stop_recording(cam_id)
    
    def start_recording(self, camera_id: int, camera_name: str, stream_manager) -> bool:
        """Start recording for a camera"""
        try:
            if camera_id in self.recorders:
                logger.warning(f"Camera {camera_id} is already recording")
                return True
            
            recorder = CameraRecorder(camera_id, camera_name, self.recordings_path)
            self.recorders[camera_id] = recorder
            recorder.start(stream_manager)
            
            return True
        except Exception as e:
            logger.error(f"Failed to start recording for camera {camera_id}: {e}")
            return False
    
    def stop_recording(self, camera_id: int):
        """Stop recording for a camera"""
        if camera_id in self.recorders:
            self.recorders[camera_id].stop()
            del self.recorders[camera_id]
    
    def is_recording(self, camera_id: int) -> bool:
        """Check if camera is recording"""
        return camera_id in self.recorders and self.recorders[camera_id].is_recording
    
    def get_recording_count(self) -> int:
        """Get number of active recordings"""
        return len(self.recorders)
    
    def restart_all_recordings(self):
        """Restart all active recordings to apply new settings"""
        logger.info("♻️ Restarting all recordings to apply new settings")
        try:
             # Snapshot keys to avoid runtime modification issues
             for cam_id, recorder in list(self.recorders.items()):
                 if recorder.is_recording:
                     logger.info(f"♻️ Restarting Camera {cam_id}")
                     recorder.stop()
                     # Allow brief pause for process cleanup
                     time.sleep(0.5) 
                     recorder.start(None) # Stream manager not needed for FFmpeg
        except Exception as e:
            logger.error(f"Failed to restart recordings: {e}")

    def get_progress(self, camera_id: int) -> dict:
        """Get recording progress for a camera"""
        if camera_id in self.recorders:
            return self.recorders[camera_id].get_progress()
        return {'progress': 0, 'elapsed': 0, 'total': 0, 'frames': 0}


# Global instance
recording_manager = RecordingManager()

