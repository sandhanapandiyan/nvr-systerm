"""
Migration script to copy cameras from Flask SQLite DB to Django
Using direct SQLite access to avoid environment conflicts
"""
import os
import sys
import sqlite3
import django

# Setup Django
sys.path.append('/home/sandhanapandiyan/Documents/nvr design/django_nvr')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nvr_project.settings')
django.setup()

# Now we can import Django models
from cameras.models import Camera

def migrate_cameras():
    """Migrate cameras from Flask to Django using direct SQLite"""
    print("=" * 60)
    print("Camera Migration: Flask → Django")
    print("=" * 60)
    
    # Connect directly to Flask database
    flask_db_path = '/home/sandhanapandiyan/Documents/nvr design/data/nvr.db'
    
    if not os.path.exists(flask_db_path):
        print(f"\n❌ Flask database not found at: {flask_db_path}")
        return
    
    conn = sqlite3.connect(flask_db_path)
    cursor = conn.cursor()
    
    # Get cameras from Flask database
    cursor.execute("SELECT id, name, rtsp_url, type, recording, streaming FROM cameras")
    flask_cameras = cursor.fetchall()
    conn.close()
    
    print(f"\nFound {len(flask_cameras)} cameras in Flask database")
    
    if not flask_cameras:
        print("\n⚠️  No cameras found in Flask database to migrate")
        return
    
    # Migrate each camera
    migrated = 0
    skipped = 0
    
    for cam_data in flask_cameras:
        camera_id, name, rtsp_url, camera_type, recording, streaming = cam_data
        
        # Normalize camera type
        camera_type = (camera_type or 'RTSP').upper()
        
        # Check if camera already exists in Django
        existing = Camera.objects.filter(rtsp_url=rtsp_url).first()
        
        if existing:
            print(f"\n⏭️  Skipping '{name}' - already exists in Django")
            skipped += 1
            continue
        
        # Create camera in Django
        try:
            django_camera = Camera.objects.create(
                name=name,
                camera_type=camera_type,
                rtsp_url=rtsp_url,
                is_streaming=bool(streaming),
                is_recording=bool(recording),
                status='offline'  # Default to offline, will update when streaming starts
            )
            
            print(f"\n✅ Migrated: '{name}'")
            print(f"   Type: {camera_type}")
            print(f"   URL: {rtsp_url}")
            print(f"   Streaming: {'Yes' if streaming else 'No'}")
            print(f"   Recording: {'Yes' if recording else 'No'}")
            print(f"   Django ID: {django_camera.id}")
            
            migrated += 1
            
        except Exception as e:
            print(f"\n❌ Error migrating '{name}': {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"Migration Complete!")
    print(f"  ✅ Migrated: {migrated} cameras")
    print(f"  ⏭️  Skipped: {skipped} cameras (already exist)")
    print("=" * 60)
    
    # Show all Django cameras
    print("\n📋 All cameras in Django database:")
    all_cameras = Camera.objects.all()
    
    if all_cameras:
        for cam in all_cameras:
            status_icon = "🟢" if cam.status == 'online' else "🔴"
            stream_icon = "▶️" if cam.is_streaming else "⏸️"
            record_icon = "🔴" if cam.is_recording else "⚪"
            print(f"  {status_icon} {stream_icon} {record_icon} {cam.name} ({cam.camera_type}) - ID: {cam.id}")
    else:
        print("  No cameras in Django database")
    
    print(f"\n💡 View cameras in admin panel: http://localhost:5000/admin/cameras/camera/")
    print(f"💡 View cameras via API: http://localhost:5000/api/cameras/")
    print(f"\n✨ Migration successful! Your cameras are now in Django!")

if __name__ == '__main__':
    migrate_cameras()
