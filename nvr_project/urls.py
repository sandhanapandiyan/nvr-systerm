"""
NVR URL Configuration - Pure Django MVT
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from cameras.views import (
    live_view,
    cameras_view,
    add_camera,
    delete_camera,
    toggle_stream,
    toggle_recording,
    settings_view,
    failsafe_view,
    playback_view,
    exports_view,
    export_video,
    camera_stream,
    serve_video_file,  # Renamed
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication
    path('login', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Pages
    path('', live_view, name='live_view'),
    path('cameras', cameras_view, name='cameras'),
    path('settings', settings_view, name='settings'),
    path('failsafe', failsafe_view, name='failsafe'),
    path('playback', playback_view, name='playback'),
    path('exports', exports_view, name='exports'),
    
    # Camera Actions
    path('cameras/add', add_camera, name='add_camera'),
    path('cameras/<int:camera_id>/delete', delete_camera, name='delete_camera'),
    path('cameras/<int:camera_id>/toggle-stream', toggle_stream, name='toggle_stream'),
    path('cameras/<int:camera_id>/toggle-recording', toggle_recording, name='toggle_recording'),
    
    # Streaming
    path('stream/<int:camera_id>', camera_stream, name='camera_stream'),
    
    # Media Serving (Video Files)
    path('media/recordings/<int:camera_id>/<str:recording_id>', serve_video_file, name='serve_video_file'),
    
    # Export Action
    path('export', export_video, name='export_video'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
