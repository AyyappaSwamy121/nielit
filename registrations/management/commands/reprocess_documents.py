from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from registrations.models import UploadedDocument
from utilities.image_optimizer import process_and_optimize_image

class Command(BaseCommand):
    help = 'Reprocess existing optimized documents from their original files using updated processing policies'

    def add_arguments(self, parser):
        parser.add_argument('--application', type=str, help='Application number to process (e.g. CSC202600001)')
        parser.add_argument('--document', type=int, help='Specific document ID to process')
        parser.add_argument('--all', action='store_true', help='Process all documents in the database')

    def handle(self, *args, **options):
        if not (options['application'] or options['document'] or options['all']):
            self.stdout.write(self.style.ERROR('Must specify --application, --document, or --all'))
            return

        queryset = UploadedDocument.objects.all()

        if options['application']:
            queryset = queryset.filter(application__application_number=options['application'])
            self.stdout.write(f"Filtering by application: {options['application']}")
            
        if options['document']:
            queryset = queryset.filter(id=options['document'])
            self.stdout.write(f"Filtering by document ID: {options['document']}")
            
        if not queryset.exists():
            self.stdout.write(self.style.WARNING("No documents found matching criteria."))
            return

        success_count = 0
        error_count = 0

        for doc in queryset:
            self.stdout.write(f"\nDOCUMENT ID: {doc.id}")
            self.stdout.write(f"Type: {doc.doc_type}")
            
            if not doc.original_file or not doc.original_file.name:
                self.stdout.write(self.style.ERROR("  -> Error: No original file attached. Skipping."))
                error_count += 1
                continue

            try:
                self.stdout.write(f"Original file: {doc.original_file.name}")
                self.stdout.write(f"  Size: {doc.original_file_size or 0} bytes")
                
                # Run the newly rewritten image optimizer on the ORIGINAL FILE
                # Pass original_file to process_and_optimize_image
                doc.original_file.open('rb')
                file_info = process_and_optimize_image(doc.original_file, doc.doc_type)
                doc.original_file.close()

                # file_info contains optimized_file, metadata etc.
                self.stdout.write(f"Processing Policy: {file_info.get('processing_policy', 'UNKNOWN')}")
                
                optimized_content = file_info.get('optimized_file')
                
                # Delete old compressed file from storage if it exists to avoid bloat
                if doc.compressed_file and doc.compressed_file.name:
                    doc.compressed_file.delete(save=False)
                    
                if optimized_content:
                    doc.compressed_file.save('optimized.jpg', optimized_content, save=False)
                    self.stdout.write(f"Output: {file_info.get('image_width')}x{file_info.get('image_height')}, {file_info.get('optimized_file_size')} bytes")
                else:
                    self.stdout.write("Output: No optimized file generated (Preserved Original)")

                doc.original_file_size = file_info.get('original_file_size')
                doc.optimized_file_size = file_info.get('optimized_file_size')
                doc.image_width = file_info.get('image_width')
                doc.image_height = file_info.get('image_height')
                doc.mime_type = file_info.get('mime_type')
                doc.compression_percentage = file_info.get('compression_percentage')
                
                if 'jpeg_quality' in file_info:
                    doc.jpeg_quality = file_info['jpeg_quality']
                if 'validation_status' in file_info:
                    doc.validation_status = file_info['validation_status']
                if 'processing_policy' in file_info:
                    doc.processing_policy = file_info['processing_policy']

                doc.save()
                success_count += 1
                self.stdout.write(self.style.SUCCESS("  -> Successfully reprocessed."))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Exception occurred: {str(e)}"))
                error_count += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone. Successfully reprocessed {success_count} documents. {error_count} errors."))
