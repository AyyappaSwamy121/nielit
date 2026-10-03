import os
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from registrations.models import StudentApplication
from utilities.image_optimizer import process_and_optimize_image

class Command(BaseCommand):
    help = 'Reprocesses existing original files for Passport, Signature, and Left Thumb using the current optimization rules'

    def add_arguments(self, parser):
        parser.add_argument('--application-id', type=int, required=True, help='ID of the StudentApplication to reprocess')

    def handle(self, *args, **options):
        app_id = options['application_id']
        try:
            app = StudentApplication.objects.get(id=app_id)
        except StudentApplication.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'StudentApplication ID {app_id} does not exist.'))
            return

        docs = app.documents.filter(original_file__isnull=False)
        target_types = ['passport', 'signature', 'thumb']
        
        reprocessed = 0
        for doc in docs:
            dt = doc.doc_type.lower()
            if not any(t in dt for t in target_types):
                continue
                
            self.stdout.write(f'Reprocessing {doc.doc_type} for Application {app_id}...')
            
            try:
                # Run optimizer on original file
                result = process_and_optimize_image(doc.original_file.file, doc.doc_type)
                
                # Atomically replace the optimized file if it exists, without altering folder structure
                # The .save() method with save=True updates the model field automatically.
                if doc.compressed_file:
                    # Remove old compressed file physically to prevent dangling files
                    if os.path.isfile(doc.compressed_file.path):
                        os.remove(doc.compressed_file.path)
                
                # We need to construct the expected filename.
                # get_upload_path normally handles this, but since we are replacing it, 
                # we can just use doc.original_file.name and change 'original.jpg' to 'optimized.jpg' if it exists.
                if 'original' in doc.original_file.name:
                    new_name = doc.original_file.name.replace('original', 'optimized')
                else:
                    # fallback
                    new_name = doc.original_file.name + '_optimized.jpg'
                    
                doc.compressed_file.save(os.path.basename(new_name), result['optimized_file'], save=False)
                
                # Update metadata
                doc.optimized_file_size = result['optimized_file_size']
                doc.image_width = result['image_width']
                doc.image_height = result['image_height']
                doc.mime_type = result['mime_type']
                doc.compression_percentage = result['compression_percentage']
                doc.save()
                
                self.stdout.write(self.style.SUCCESS(f'Successfully reprocessed {doc.doc_type}'))
                reprocessed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to process {doc.doc_type}: {str(e)}'))
                
        self.stdout.write(self.style.SUCCESS(f'Finished reprocessing {reprocessed} images for Application {app_id}.'))
