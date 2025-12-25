#!/usr/bin/env python
"""
Import all existing video files to database
"""

import os
import sys
import django
from pathlib import Path
from datetime import datetime, timedelta

# Setup Django
sys.path.insert(0, '/home/sandhanapandiyan/Documents/nvr design/django_nvr')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nvr_project.settings')
django.setup()

from cameras.models import Camera
from recordings.models import Recording

def import_all_recordings():
    """Import all video files from recordings folder to database"""
    
    recordings_path = Path.home() / "Desktop" / "NVR_Recordings"
    
    print(f"🔍 Scanning for video files in: {recordings_path}")
    
    # Find all MP4 files
    video_files = list(recordings_path.glob("**/*.mp4"))
    print(f"📹 Found {len(video_files)} video files")
    
    # Get existing database entries
    existing_files = set(Recording.objects.values_list('filepath', flat=True))
    print(f"💾 Database has {len(existing_files)} recordings")
    
    imported = 0
    skipped = 0
    errors = 0
    
    for video_file in video_files:
        file_path_str = str(video_file)
        
        # Skip if already in database
        if file_path_str in existing_files:
            skipped += 1
            continue
        
        try:
            # Extract camera ID from path (e.g., camera_4)
            parts = video_file.parts
            camera_folder = None
            for part in parts:
                if part.startswith('camera_'):
                    camera_folder = part
                    break
            
            if not camera_folder:
                print(f"⚠️  Could not find camera folder for: {video_file.name}")
                errors += 1
                continue
            
            camera_id = int(camera_folder.replace('camera_', ''))
            
            try:
                camera = Camera.objects.get(id=camera_id)
            except Camera.DoesNotExist:
                print(f"⚠️  Camera {camera_id} not found in database, skipping {video_file.name}")
                errors += 1
                continue
            
            # Get file info
            stat = video_file.stat()
            file_size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            
            # Assume 5 minute segments
            duration = 300
            end_time = mtime + timedelta(seconds=duration)
            
            # Create database entry
            Recording.objects.create(
                camera=camera,
                filepath=file_path_str,
                filename=video_file.name,
                start_time=mtime,
                end_time=end_time,
                file_size=file_size,
                duration=duration,
                recording_date=mtime.date()
            )
            
            imported += 1
            print(f"✅ Imported: {video_file.name} ({file_size/1024/1024:.2f}MB)")
            
        except Exception as e:
            errors += 1
            print(f"❌ Error importing {video_file.name}: {e}")
    
    print("\n" + "="*60)
    print(f"📊 Import Summary:")
    print(f"   ✅ Imported: {imported}")
    print(f"   ⏭️  Skipped (already in DB): {skipped}")
    print(f"   ❌ Errors: {errors}")
    print(f"   📹 Total in Database: {Recording.objects.count()}")
    print("="*60)

if __name__ == '__main__':
    import_all_recordings()
