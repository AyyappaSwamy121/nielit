import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from registrations.models import StudentApplication, UploadedDocument
from utilities.folder_manager import get_student_folder_name, FOLDER_MAPPING

class Command(BaseCommand):
    help = 'Migrates existing student media folders from app_number to aadhaar_number format.'

    def handle(self, *args, **options):
        applications = StudentApplication.objects.all()
        migrated_count = 0
        error_count = 0
        skip_count = 0

        for app in applications:
            try:
                # Target storage folder
                new_folder_name = get_student_folder_name(app.aadhaar_number, app.full_name)
                old_folder_name = f"{app.application_number}_{app.full_name.replace(' ', '_')}"
                
                # Assign to DB
                if not app.storage_folder or app.storage_folder != new_folder_name:
                    app.storage_folder = new_folder_name
                    app.save(update_fields=['storage_folder'])

                old_path_abs = os.path.join(settings.MEDIA_ROOT, old_folder_name)
                new_path_abs = os.path.join(settings.MEDIA_ROOT, new_folder_name)
                
                # Check if old folder exists on disk
                moved_anything = False
                if os.path.exists(old_path_abs) and old_path_abs != new_path_abs:
                    # Move folder
                    if not os.path.exists(new_path_abs):
                        os.makedirs(new_path_abs, exist_ok=True)
                        
                    # We iterate through everything in old folder and move it to new
                    # But since the internal structure ALSO changed (e.g. Passport_Photo -> Passport),
                    # we need to be careful. The easiest is to just update paths in DB and let os rename handle it, 
                    # but wait! If the subfolders changed names, we must rename the subfolders too!
                    
                    for doc in app.documents.all():
                        # Determine old paths
                        old_doc_type = doc.doc_type
                        new_doc_type = FOLDER_MAPPING.get(old_doc_type, old_doc_type)
                        
                        # original_file
                        if doc.original_file and doc.original_file.name:
                            old_file_path = os.path.join(settings.MEDIA_ROOT, doc.original_file.name)
                            if os.path.exists(old_file_path):
                                filename = os.path.basename(doc.original_file.name)
                                new_rel_path = f"{new_folder_name}/{new_doc_type}/{filename}"
                                new_file_path = os.path.join(settings.MEDIA_ROOT, new_rel_path)
                                
                                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
                                shutil.move(old_file_path, new_file_path)
                                doc.original_file.name = new_rel_path
                                moved_anything = True
                                
                        # compressed_file
                        if doc.compressed_file and doc.compressed_file.name:
                            old_file_path = os.path.join(settings.MEDIA_ROOT, doc.compressed_file.name)
                            if os.path.exists(old_file_path):
                                filename = os.path.basename(doc.compressed_file.name)
                                new_rel_path = f"{new_folder_name}/{new_doc_type}/{filename}"
                                new_file_path = os.path.join(settings.MEDIA_ROOT, new_rel_path)
                                
                                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
                                shutil.move(old_file_path, new_file_path)
                                doc.compressed_file.name = new_rel_path
                                moved_anything = True
                        
                        doc.save()

                    # Handle acknowledgements
                    ack_fields = ['acknowledgement_pdf', 'acknowledgement_png', 'acknowledgement_jpg']
                    for field in ack_fields:
                        file_field = getattr(app, field)
                        if file_field and file_field.name:
                            old_file_path = os.path.join(settings.MEDIA_ROOT, file_field.name)
                            if os.path.exists(old_file_path):
                                filename = os.path.basename(file_field.name)
                                new_rel_path = f"{new_folder_name}/acknowledgement/{filename}"
                                new_file_path = os.path.join(settings.MEDIA_ROOT, new_rel_path)
                                
                                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
                                shutil.move(old_file_path, new_file_path)
                                file_field.name = new_rel_path
                                app.save(update_fields=[field])
                                moved_anything = True

                    # Try to clean up empty old folders
                    try:
                        for root, dirs, files in os.walk(old_path_abs, topdown=False):
                            for name in dirs:
                                os.rmdir(os.path.join(root, name))
                        os.rmdir(old_path_abs)
                    except OSError:
                        pass # Ignore if not empty
                        
                if moved_anything:
                    self.stdout.write(self.style.SUCCESS(f"Migrated {app.application_number} -> {new_folder_name}"))
                    migrated_count += 1
                else:
                    self.stdout.write(f"Skipped {app.application_number} (already migrated or no files)")
                    skip_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error migrating {app.application_number}: {str(e)}"))
                error_count += 1

        self.stdout.write(self.style.SUCCESS(f"Migration complete! Migrated: {migrated_count}, Skipped: {skip_count}, Errors: {error_count}"))
