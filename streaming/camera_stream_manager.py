"""
Camera Stream Manager for Django NVR
Handles RTSP stream capture and frame caching for multiple cameras
"""

import cv2
import threading
import time
import logging
from collections import deque
from typing import Optional, Dict
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class CameraStream:
    """Manages a single camera RTSP stream"""
    
    def __init__(self, camera_id: int, rtsp_url: str, camera_name: str = None):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.camera_name = camera_name or f"Camera {camera_id}"
        self.frame = None
        self.is_running = False
        self.thread = None
        self.capture = None
        self.last_frame_time = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
    def start(self):
        """Start capturing frames from the camera"""
        if self.is_running:
            logger.warning(f"Camera {self.camera_id} is already streaming")
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_frames, daemon=True)
        self.thread.start()
        logger.info(f"Started stream for camera {self.camera_id}")
        
    def stop(self):
        """Stop capturing frames"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.capture:
            self.capture.release()
        logger.info(f"Stopped stream for camera {self.camera_id}")
        
    def _capture_frames(self):
        """Background thread to capture frames from RTSP stream"""
        while self.is_running:
            try:
                # Initialize or reinitialize capture
                if self.capture is None or not self.capture.isOpened():
                    logger.info(f"Connecting to camera {self.camera_id}: {self.rtsp_url}")
                    self.capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                    self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
                    
                    if not self.capture.isOpened():
                        logger.error(f"Failed to connect to camera {self.camera_id}")
                        self.reconnect_attempts += 1
                        
                        if self.reconnect_attempts >= self.max_reconnect_attempts:
                            logger.error(f"Max reconnect attempts reached for camera {self.camera_id}")
                            self.is_running = False
                            break
                            
                        time.sleep(5)  # Wait before retry
                        continue
                    
                    self.reconnect_attempts = 0
                    logger.info(f"Successfully connected to camera {self.camera_id}")
                
                # Read frame
                ret, frame = self.capture.read()
                
                if ret and frame is not None:
                    # Resize frame to reduce bandwidth (optional)
                    # frame = cv2.resize(frame, (1280, 720))
                    self.frame = frame
                    self.last_frame_time = time.time()
                else:
                    logger.warning(f"Failed to read frame from camera {self.camera_id}")
                    time.sleep(0.1)
                    
                    # Check if stream is dead
                    if self.last_frame_time and (time.time() - self.last_frame_time > 10):
                        logger.error(f"Stream appears dead for camera {self.camera_id}, reconnecting...")
                        if self.capture:
                            self.capture.release()
                        self.capture = None
                        
            except Exception as e:
                logger.error(f"Error capturing frame from camera {self.camera_id}: {e}")
                if self.capture:
                    self.capture.release()
                self.capture = None
                time.sleep(1)
                
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame without overlays"""
        return self.frame if self.frame is not None else None

        
    def is_alive(self) -> bool:
        """Check if stream is alive"""
        if not self.is_running:
            return False
        if self.last_frame_time is None:
            return False
        return (time.time() - self.last_frame_time) < 10  # Consider alive if frame within last 10 seconds


class CameraStreamManager:
    """Manages multiple camera streams"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.streams: Dict[int, CameraStream] = {}
        self._initialized = True
        logger.info("CameraStreamManager initialized")
        
    def start_stream(self, camera_id: int, rtsp_url: str, camera_name: str = None) -> bool:
        """Start streaming for a camera"""
        try:
            # Stop existing stream if any
            if camera_id in self.streams:
                self.stop_stream(camera_id)
            
            # Create and start new stream
            stream = CameraStream(camera_id, rtsp_url, camera_name)
            self.streams[camera_id] = stream
            stream.start()
            
            # Wait a moment for connection
            time.sleep(2)
            
            return True
        except Exception as e:
            logger.error(f"Failed to start stream for camera {camera_id}: {e}")
            return False
            
    def stop_stream(self, camera_id: int):
        """Stop streaming for a camera"""
        if camera_id in self.streams:
            self.streams[camera_id].stop()
            del self.streams[camera_id]
            logger.info(f"Removed stream for camera {camera_id}")
            
    def get_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """Get latest frame for a camera"""
        if camera_id in self.streams:
            return self.streams[camera_id].get_frame()
        return None
        
    def is_streaming(self, camera_id: int) -> bool:
        """Check if camera is streaming"""
        return camera_id in self.streams and self.streams[camera_id].is_alive()
        
    def stop_all(self):
        """Stop all camera streams"""
        camera_ids = list(self.streams.keys())
        for camera_id in camera_ids:
            self.stop_stream(camera_id)
        logger.info("Stopped all camera streams")
        
    def get_active_count(self) -> int:
        """Get count of active streams"""
        return sum(1 for stream in self.streams.values() if stream.is_alive())


# Global manager instance
stream_manager = CameraStreamManager()
