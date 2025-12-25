"""
Main NVR Views - Full Stack Application with Separate Templates
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from cameras.models import Camera, CameraSettings
from recordings.models import Recording, ExportedVideo
import json


@login_required
def live_view(request):
    """Live View page"""
    return render(request, 'live_view.html')


@login_required
def cameras_view(request):
    """Camera Management page"""
    return render(request, 'cameras.html')


@login_required
def settings_view(request):
    """Settings page"""
    return render(request, 'settings.html')


@login_required
def failsafe_view(request):
    """Failsafe Monitor page"""
    return render(request, 'failsafe.html')


@login_required
def playback_view(request):
    """Playback page"""
    return render(request, 'playback.html')


@login_required
def exports_view(request):
    """Exports page"""
    return render(request, 'exports.html')


# API endpoints remain the same
@login_required
def get_cameras_json(request):
    """Get all cameras as JSON"""
    cameras = Camera.objects.all()
    camera_list = []
    
    for cam in cameras:
        camera_list.append({
            'id': str(cam.id),
            'name': cam.name,
            'type': cam.camera_type.lower(),
            'rtsp_url': cam.rtsp_url,
            'streaming': cam.is_streaming,
            'recording': cam.is_recording,
            'status': cam.status,
        })
    
    return JsonResponse(camera_list, safe=False)


@login_required
def add_camera_json(request):
    """Add a new camera"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            camera = Camera.objects.create(
                name=data.get('name'),
                camera_type=data.get('type', 'RTSP').upper(),
                username=data.get('username', ''),
                password=data.get('password', ''),
                ip_address=data.get('ip_address', ''),
                port=data.get('port', 554),
                stream_path=data.get('stream_path', '/'),
                rtsp_url=data.get('rtsp_url', ''),
            )
            return JsonResponse({
                'success': True,
                'camera': {
                    'id': str(camera.id),
                    'name': camera.name,
                    'rtsp_url': camera.rtsp_url,
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def delete_camera_json(request, camera_id):
    """Delete a camera"""
    try:
        camera = Camera.objects.get(id=camera_id)
        camera.delete()
        return JsonResponse({'success': True})
    except Camera.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Camera not found'})


@login_required
def start_stream_json(request, camera_id):
    """Start streaming a camera"""
    try:
        camera = Camera.objects.get(id=camera_id)
        camera.is_streaming = True
        camera.status = 'online'
        camera.save()
        return JsonResponse({'success': True, 'message': 'Stream started'})
    except Camera.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Camera not found'})


@login_required
def stop_stream_json(request, camera_id):
    """Stop streaming a camera"""
    try:
        camera = Camera.objects.get(id=camera_id)
        camera.is_streaming = False
        camera.status = 'offline'
        camera.save()
        return JsonResponse({'success': True, 'message': 'Stream stopped'})
    except Camera.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Camera not found'})


@login_required
def start_recording_json(request, camera_id):
    """Start recording a camera"""
    try:
        camera = Camera.objects.get(id=camera_id)
        camera.is_recording = True
        camera.save()
        return JsonResponse({'success': True, 'message': 'Recording started'})
    except Camera.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Camera not found'})


@login_required
def stop_recording_json(request, camera_id):
    """Stop recording a camera"""
    try:
        camera = Camera.objects.get(id=camera_id)
        camera.is_recording = False
        camera.save()
        return JsonResponse({'success': True, 'message': 'Recording stopped'})
    except Camera.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Camera not found'})


@login_required
def get_recordings_json(request, camera_id):
    """Get recordings for a camera"""
    recordings = Recording.objects.filter(camera_id=camera_id).order_by('-start_time')[:100]
    recording_list = []
    
    for rec in recordings:
        recording_list.append({
            'id': rec.id,
            'filename': rec.filename,
            'start_time': rec.start_time.isoformat(),
            'end_time': rec.end_time.isoformat(),
            'duration': rec.duration,
            'size': rec.file_size,
        })
    
    return JsonResponse(recording_list, safe=False)


@login_required
def get_timeline_json(request, camera_id):
    """Get timeline data for a camera"""
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter required'}, status=400)
    
    from datetime import datetime
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    recordings = Recording.objects.filter(
        camera_id=camera_id,
        recording_date=date
    ).order_by('start_time')
    
    timeline = []
    for rec in recordings:
        timeline.append({
            'id': rec.id,
            'start': rec.start_time.isoformat(),
            'end': rec.end_time.isoformat(),
            'filename': rec.filename,
        })
    
    return JsonResponse({'timeline': timeline})


@login_required
def get_settings_json(request):
    """Get system settings"""
    settings_obj = CameraSettings.get_settings()
    return JsonResponse({
        'segment_duration': settings_obj.segment_duration,
        'retention_days': settings_obj.retention_days,
        'max_storage_gb': settings_obj.max_storage_gb,
        'video_format': 'mp4',
        'video_codec': 'copy',
        'audio_codec': 'aac',
    })


@login_required
def update_settings_json(request):
    """Update system settings"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            settings_obj = CameraSettings.get_settings()
            
            if 'segment_duration' in data:
                settings_obj.segment_duration = data['segment_duration']
            if 'retention_days' in data:
                settings_obj.retention_days = data['retention_days']
            if 'max_storage_gb' in data:
                settings_obj.max_storage_gb = data['max_storage_gb']
            
            settings_obj.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def get_exports_json(request):
    """Get list of exported videos"""
    exports = ExportedVideo.objects.all().order_by('-export_date')[:50]
    export_list = []
    
    for exp in exports:
        export_list.append({
            'filename': exp.filename,
            'camera': exp.camera.name,
            'start_time': exp.start_time.isoformat(),
            'end_time': exp.end_time.isoformat(),
            'size': exp.file_size,
            'format': exp.format,
        })
    
    return JsonResponse(export_list, safe=False)
