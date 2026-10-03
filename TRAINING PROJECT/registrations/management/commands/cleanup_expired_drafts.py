from django.core.management.base import BaseCommand
import os
import shutil
import time
from django.conf import settings

class Command(BaseCommand):
    help = 'Cleans up temporary uploaded files in media/temp_uploads/ that are older than 24 hours.'

    def handle(self, *args, **kwargs):
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        if not os.path.exists(temp_dir):
            self.stdout.write(self.style.SUCCESS("Temporary uploads directory does not exist. Nothing to clean."))
            return

        now = time.time()
        age_limit = 24 * 60 * 60  # 24 hours in seconds
        
        deleted_count = 0
        
        for session_folder in os.listdir(temp_dir):
            folder_path = os.path.join(temp_dir, session_folder)
            
            # Ensure it's a directory
            if os.path.isdir(folder_path):
                folder_stat = os.stat(folder_path)
                # If folder was created or last modified more than 24 hours ago
                if (now - folder_stat.st_mtime) > age_limit:
                    try:
                        shutil.rmtree(folder_path)
                        deleted_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Deleted expired draft folder: {session_folder}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to delete {session_folder}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Cleanup complete. Removed {deleted_count} expired temporary draft folders."))
