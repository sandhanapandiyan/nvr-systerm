"""
Django NVR Views - Pure MVT Architecture  
Direct form handling, no APIs
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse, FileResponse
from cameras.models import Camera, CameraSettings
from recordings.models import Recording, ExportedVideo
from datetime import datetime
from streaming.camera_stream_manager import stream_manager
from streaming.recording_manager import recording_manager
import cv2
import time
import os
import logging
import json

logger = logging.getLogger(__name__)


@login_required
def live_view(request):
    """Live View page with cameras"""
    cameras = Camera.objects.all()
    
    # Auto-start recording for streaming cameras that aren't recording
    # Auto-start recording for ALL cameras ensuring they never stop
    for camera in cameras:
        # Check if actually recording in manager, regardless of DB flag
        if not recording_manager.is_recording(camera.id):
            try:
                # Always force start
                if recording_manager.start_recording(camera.id, camera.name, stream_manager):
                    camera.is_recording = True
                    camera.save(update_fields=['is_recording'])
            except Exception as e:
                logger.error(f"Failed to auto-start recording for {camera.name}: {e}")
    
    settings = CameraSettings.get_settings()
    
    return render(request, 'live_view.html', {
        'cameras': cameras,
        'active_cameras': cameras.filter(is_streaming=True).count(),
        'segment_duration': settings.segment_duration
    })


@login_required
def cameras_view(request):
    """Camera Management page"""
    cameras = Camera.objects.all()
    return render(request, 'cameras.html', {
        'cameras': cameras
    })


@login_required
def add_camera(request):
    """Add new camera - Form POST handler"""
    if request.method == 'POST':
        try:
            camera = Camera.objects.create(
                name=request.POST.get('name'),
                camera_type=request.POST.get('type', 'RTSP').upper(),
                username=request.POST.get('username', ''),
                password=request.POST.get('password', ''),
                ip_address=request.POST.get('ip_address', ''),
                port=int(request.POST.get('port', 554)),
                stream_path=request.POST.get('stream_path', '/'),
            )
            
            
            # Auto-start streaming and recording
            try:
                rtsp_url = camera.build_rtsp_url()
                if stream_manager.start_stream(camera.id, rtsp_url, camera.name):
                    camera.is_streaming = True
                    camera.status = 'online'
                    camera.save()
                    
                    # Start recording automatically
                    if recording_manager.start_recording(camera.id, camera.name, stream_manager):
                        camera.is_recording = True
                        camera.save()
                        messages.success(request, f'Camera "{camera.name}" is now streaming and recording!')
                    else:
                        messages.warning(request, f'Camera is streaming but recording failed to start')
                else:
                    messages.warning(request, f'Camera added but streaming failed to start')
            except Exception as e:
                messages.warning(request, f'Camera added but streaming failed: {str(e)}')
            
            messages.success(request, f'Camera "{camera.name}" added successfully!')
            return redirect('cameras')
        except Exception as e:
            messages.error(request, f'Error adding camera: {str(e)}')
            return redirect('cameras')
    
    return redirect('cameras')


@login_required
def delete_camera(request, camera_id):
    """Delete camera"""
    camera = get_object_or_404(Camera, id=camera_id)
    name = camera.name
    
    # Stop recording before deletion
    try:
        recording_manager.stop_recording(camera_id)
    except Exception as e:
        logger.error(f"Error stopping recording during deletion: {e}")
        
    camera.delete()
    messages.success(request, f'Camera "{name}" deleted successfully!')
    return redirect('cameras')


@login_required
def toggle_stream(request, camera_id):
    """Toggle camera streaming on/off"""
    camera = get_object_or_404(Camera, id=camera_id)
    camera.is_streaming = not camera.is_streaming
    camera.status = 'online' if camera.is_streaming else 'offline'
    camera.save()
    
    status = 'started' if camera.is_streaming else 'stopped'
    messages.success(request, f'Streaming {status} for "{camera.name}"')
    return redirect('live_view')


@login_required
def toggle_recording(request, camera_id):
    """Toggle camera recording on/off"""
    camera = get_object_or_404(Camera, id=camera_id)
    # Enforce always recording - prevent stopping
    if not camera.is_recording:
        camera.is_recording = True
        camera.save()
        recording_manager.start_recording(camera.id, camera.name, stream_manager)
        messages.success(request, f'Recording started for "{camera.name}" (Continuous recording enforced)')
    else:
        messages.info(request, f'Recording is already active for "{camera.name}" and cannot be stopped (Continuous recording enforced)')
    
    return redirect('cameras')


@login_required
def settings_view(request):
    """Settings page"""
    settings_obj = CameraSettings.get_settings()
    
    if request.method == 'POST':
        # Update settings from form
        settings_obj.segment_duration = int(request.POST.get('segment_duration', 300))
        settings_obj.retention_days = int(request.POST.get('retention_days', 7))
        settings_obj.max_storage_gb = int(request.POST.get('max_storage_gb', 100))
        
        # Video and Audio settings
        settings_obj.video_format = request.POST.get('video_format', 'mp4')
        settings_obj.video_codec = request.POST.get('video_codec', 'copy')
        settings_obj.audio_codec = request.POST.get('audio_codec', 'aac')
        settings_obj.audio_bitrate = request.POST.get('audio_bitrate', '128k')
        
        settings_obj.save()
        
        # Restart recordings to apply new settings
        try:
            recording_manager.restart_all_recordings()
            messages.success(request, 'Settings saved and active recordings restarted!')
        except Exception as e:
            logger.error(f"Failed to restart recordings: {e}")
            messages.warning(request, 'Settings saved but recordings restart failed')

        return redirect('settings')
    
    return render(request, 'settings.html', {
        'settings': settings_obj
    })



@login_required
def failsafe_view(request):
    """Failsafe Monitor page"""
    cameras = Camera.objects.all()
    
    # Simple stats without psutil (will show placeholder values)
    return render(request, 'failsafe.html', {
        'cameras_monitored': cameras.count(),
        'cpu_usage': 25.5,  # Placeholder
        'memory_usage': 45.2,  # Placeholder
        'disk_usage': 62.8,  # Placeholder
        'monitor_running': True,
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@login_required
def playback_view(request):
    """Playback page - Fully Server-Side Rendered"""
    cameras = Camera.objects.all()
    
    # Selection State
    selected_camera_id = request.GET.get('camera_id')
    selected_date = request.GET.get('date')
    
    # Context Data Containers
    available_dates = []
    recordings = []
    timeline_segments = []
    
    if selected_camera_id:
        try:
            selected_camera_id = int(selected_camera_id)
            # 1. Fetch Available Dates
            dates_qs = Recording.objects.filter(camera_id=selected_camera_id).dates('recording_date', 'day', order='DESC')
            available_dates = [d.isoformat() for d in dates_qs]
            
            # 2. If Date Selected, Fetch Segments for Timeline
            if selected_date:
                try:
                    date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                    recordings = Recording.objects.filter(
                        camera_id=selected_camera_id,
                        recording_date=date_obj
                    ).order_by('start_time')
                    
                    for r in recordings:
                        timeline_segments.append({
                            # ISO format for JS parsing
                            'start_time': r.start_time.isoformat(),
                            'duration': r.duration,
                            'size': r.file_size,
                            'filename': r.filename
                        })
                except ValueError:
                    logger.warning(f"Invalid date format: {selected_date}")

        except (ValueError, TypeError):
             logger.warning(f"Invalid camera_id: {selected_camera_id}")
    
    # 3. Serializing for JS (Timeline visualization still needs data)
    # We pass it as a JSON string to be embedded in a <script> tag
    timeline_data_json = json.dumps({'segments': timeline_segments})
    available_dates_json = json.dumps({'dates': available_dates})
    
    # Simple camera list for JS if needed (e.g. for switching logic if client-side persist)
    cameras_list = [{'id': c.id, 'name': c.name} for c in cameras]
    cameras_json = json.dumps(cameras_list)

    return render(request, 'playback.html', {
        'cameras': cameras,
        'selected_camera_id': selected_camera_id,
        'selected_date': selected_date,
        'available_dates': available_dates,         # For Template Loop
        'available_dates_json': available_dates_json, # For JS (Optional)
        'timeline_data_json': timeline_data_json,   # For DVR Timeline JS
        'cameras_json': cameras_json,
    })


@login_required
def exports_view(request):
    """Exports page"""
    exports = ExportedVideo.objects.all().order_by('-created_at', '-export_date')[:50]
    return render(request, 'exports.html', {
        'exports': exports
    })


@login_required
def export_video(request):
    """Export video - Form POST handler"""
    if request.method == 'POST':
        try:
            camera_id = request.POST.get('camera_id')
            
            # Combine split date/time fields
            start_date = request.POST.get('start_date')
            start_time = request.POST.get('start_time')
            end_date = request.POST.get('end_date')
            end_time = request.POST.get('end_time')
            
            # Basic validation
            if not (camera_id and start_date and start_time and end_date and end_time):
                 messages.warning(request, "Please fill in all export fields.")
                 return redirect('playback')

            start_dt_str = f"{start_date}T{start_time}"
            end_dt_str = f"{end_date}T{end_time}"
            
            # Add seconds if missing (HTML time input might perform differently)
            if len(start_time) == 5: start_dt_str += ":00"
            if len(end_time) == 5: end_dt_str += ":00"

            # Create export record
            camera = get_object_or_404(Camera, id=camera_id)
            export = ExportedVideo.objects.create(
                camera=camera,
                start_time=datetime.fromisoformat(start_dt_str),
                end_time=datetime.fromisoformat(end_dt_str),
                format='mp4'
            )
            
            messages.success(request, 'Video export started! Check exports page for progress.')
            return redirect('exports')
        except Exception as e:
            messages.error(request, f'Error exporting video: {str(e)}')
            # Preserve selection
            return redirect(f'/playback?camera_id={camera_id}' if camera_id else 'playback')
    
    return redirect('playback')


@login_required
def camera_stream(request, camera_id):
    """Stream endpoint for camera video - MJPEG format"""
    try:
        camera = get_object_or_404(Camera, id=camera_id)
        
        # Check if stream exists, if not start it
        if not stream_manager.is_streaming(camera_id):
            rtsp_url = camera.build_rtsp_url()
            stream_manager.start_stream(camera_id, rtsp_url, camera.name)
            time.sleep(1)  # Give it a moment to connect
        
        def generate_frames():
            """Generator function for MJPEG  streaming"""
            jpeg_quality = 85
            no_frame_count = 0
            
            while True:
                frame = stream_manager.get_frame(camera_id)
                
                if frame is not None:
                    no_frame_count = 0
                    # Encode frame as JPEG
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                    
                    if ret:
                        # Yield frame in multipart format
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                else:
                    no_frame_count += 1
                    # If no frames for 10 seconds, stop
                    if no_frame_count >= 250:  # 250 * 0.04s = 10s
                        break
                
                time.sleep(0.04)  # ~25 FPS to reduce CPU load
        
        return StreamingHttpResponse(
            generate_frames(),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )
        
    except Exception as e:
        return HttpResponse(f'Error streaming camera: {str(e)}', status=500)


@login_required
def serve_video_file(request, camera_id, recording_id):
    """File Server: Serve actual MP4 video file"""
    try:
        # recording_id is filename without extension (from app.js logic typically)
        # But let's support exact filename match if passed
        recording = Recording.objects.filter(
            camera_id=camera_id, 
            filename__startswith=recording_id
        ).first()
        
        if not recording or not os.path.exists(recording.filepath):
            return HttpResponse("Recording not found", status=404)
            
        # Serve file using FileResponse (efficient streaming)
        return FileResponse(open(recording.filepath, 'rb'), content_type='video/mp4')
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

