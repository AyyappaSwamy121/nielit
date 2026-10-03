import zipfile
import io
import os
from django.http import HttpResponse
from registrations.models import StudentApplication
from .excel_export import export_students_to_excel

def export_students_to_zip(queryset=None):
    """
    Exports the uploaded documents of the provided queryset to a highly-structured ZIP archive.
    Includes an embedded Excel sheet within the ZIP for each student or globally.
    """
    if queryset is None:
        queryset = StudentApplication.objects.all().select_related(
            'state', 'district', 'program_opting', 'status'
        )
        
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for app in queryset:
            # Root folder: Application_Number_Name
            folder_name = f"{app.application_number}_{app.full_name.replace(' ', '_')}"
            
            for doc in app.documents.all():
                doc_type_folder = doc.doc_type.capitalize() # e.g., 'Passport_photo'
                
                if doc.original_file and os.path.exists(doc.original_file.path):
                    ext = os.path.splitext(doc.original_file.name)[1]
                    zip_path = f"{folder_name}/{doc_type_folder}/original{ext}"
                    zip_file.write(doc.original_file.path, zip_path)
                    
                if doc.compressed_file and os.path.exists(doc.compressed_file.path):
                    ext = os.path.splitext(doc.compressed_file.name)[1]
                    zip_path = f"{folder_name}/{doc_type_folder}/compressed{ext}"
                    zip_file.write(doc.compressed_file.path, zip_path)
            
            # Embed a single-row Excel file specifically for this student inside their folder
            single_qs = StudentApplication.objects.filter(id=app.id).select_related(
                'state', 'district', 'program_opting', 'status'
            )
            excel_response = export_students_to_excel(single_qs)
            zip_file.writestr(f"{folder_name}/Student_Details.xlsx", excel_response.content)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="Comprehensive_Students_Export.zip"'
    return response
