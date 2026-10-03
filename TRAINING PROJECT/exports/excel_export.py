import pandas as pd
from django.http import HttpResponse
from registrations.models import StudentApplication
import os
from django.conf import settings

def get_file_size(file_field):
    if file_field and hasattr(file_field, 'path') and os.path.exists(file_field.path):
        return f"{os.path.getsize(file_field.path) / 1024:.2f} KB"
    return "N/A"

def export_students_to_excel(queryset=None):
    """
    Exports the provided queryset of StudentApplication to an Excel file with detailed fields.
    """
    if queryset is None:
        queryset = StudentApplication.objects.all().select_related(
            'state', 'district', 'program_opting', 'status'
        )
        
    data = []
    for app in queryset:
        row = {
            'Application Number': app.application_number,
            'Full Name': app.full_name,
            'Father Name': app.father_name,
            'DOB': app.dob.strftime('%Y-%m-%d') if app.dob else '',
            'Gender': app.gender,
            'Mobile': app.mobile_number,
            'Email': app.email,
            'State': app.state.name if app.state else '',
            'District': app.district.name if app.district else '',
            'Program': app.program_opting.name if app.program_opting else '',
            'Status': app.status.name if app.status else '',
            'Remarks': app.remarks,
            'Submission Date': app.submission_date.replace(tzinfo=None) if app.submission_date else '',
            'NIELIT Registration Number': app.nielit_registration_number or '',
        }
        
        # Add document file sizes
        for doc in app.documents.all():
            doc_type = doc.doc_type
            row[f'{doc_type} Original Size'] = get_file_size(doc.original_file)
            row[f'{doc_type} Compressed Size'] = get_file_size(doc.compressed_file)
            
        data.append(row)
        
    df = pd.DataFrame(data)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Advanced_Student_Export.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Student Details')
        
    return response
