import os
import shutil
from datetime import datetime
from django.conf import settings

def create_backup():
    """
    Creates a snapshot backup of the SQLite database and the media folder.
    Saves it into the /backups directory.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    current_backup_dir = os.path.join(backup_dir, f'backup_{timestamp}')
    os.makedirs(current_backup_dir)
    
    # Backup Database
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    if os.path.exists(db_path):
        shutil.copy2(db_path, os.path.join(current_backup_dir, 'db.sqlite3'))
        
    # Backup Media
    media_path = settings.MEDIA_ROOT
    if os.path.exists(media_path):
        shutil.copytree(media_path, os.path.join(current_backup_dir, 'media'))
        
    # Zip the backup
    zip_path = f"{current_backup_dir}.zip"
    shutil.make_archive(current_backup_dir, 'zip', current_backup_dir)
    
    # Remove unzipped folder to save space
    shutil.rmtree(current_backup_dir)
    
    return zip_path
