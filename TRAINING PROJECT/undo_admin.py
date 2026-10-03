import codecs

new_content = '''from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import StudentApplication, UploadedDocument
from masterdata.models import ApplicationStatus, VerificationStatus

class UploadedDocumentInline(admin.TabularInline):
    model = UploadedDocument
    extra = 0
    can_delete = False
    
    readonly_fields = [
        'doc_type', 'original_file_link', 'compressed_file_link', 'uploaded_at', 
        'document_preview', 'original_size_kb_display', 'optimized_size_kb_display', 
        'width_display', 'height_display', 'dpi_display', 'mime_type_display', 'validation_status'
    ]
    
    exclude = [
        'original_file', 'compressed_file', 'original_file_size', 'optimized_file_size', 
        'image_width', 'image_height', 'mime_type', 'compression_percentage'
    ]

    def original_file_link(self, obj):
        if obj.original_file:
            import os
            fname = os.path.basename(obj.original_file.name)
            return format_html('<a href="{}" title="{}" target="_blank" rel="noopener">{}</a>', obj.original_file.url, fname, fname)
        return "-"
    original_file_link.short_description = "Original File"

    def compressed_file_link(self, obj):
        if obj.compressed_file:
            import os
            fname = os.path.basename(obj.compressed_file.name)
            return format_html('<a href="{}" title="{}" target="_blank" rel="noopener">{}</a>', obj.compressed_file.url, fname, fname)
        return "-"
    compressed_file_link.short_description = "Compressed File"

    def original_size_kb_display(self, obj):
        if obj.original_size_kb:
            return f"{obj.original_size_kb} KB"
        return "-"
    original_size_kb_display.short_description = "Original Size"

    def optimized_size_kb_display(self, obj):
        if obj.optimized_size_kb:
            return f"{obj.optimized_size_kb} KB"
        return "-"
    optimized_size_kb_display.short_description = "Optimized Size"

    def width_display(self, obj):
        if obj.mime_type == 'application/pdf' or obj.doc_type in ['abc_screenshot', 'aadhaar_pdf', 'community_certificate', 'registration_screenshot', 'supporting_documents']:
            return "-"
        return f"{obj.image_width} px" if obj.image_width else "-"
    width_display.short_description = "Width"

    def height_display(self, obj):
        if obj.mime_type == 'application/pdf' or obj.doc_type in ['abc_screenshot', 'aadhaar_pdf', 'community_certificate', 'registration_screenshot', 'supporting_documents']:
            return "-"
        return f"{obj.image_height} px" if obj.image_height else "-"
    height_display.short_description = "Height"

    def dpi_display(self, obj):
        if obj.mime_type == 'application/pdf' or obj.doc_type in ['abc_screenshot', 'aadhaar_pdf', 'community_certificate', 'registration_screenshot', 'supporting_documents']:
            return "-"
        dpi_val = obj.actual_dpi
        if dpi_val:
            return f"{dpi_val} DPI"
        return "-"
    dpi_display.short_description = "DPI"

    def mime_type_display(self, obj):
        if obj.mime_type:
            return obj.mime_type
        return "-"
    mime_type_display.short_description = "MIME Type"
    
    def document_preview(self, obj):
        file_field = obj.compressed_file if obj.compressed_file else obj.original_file
        if not file_field:
            return "-"
            
        url = file_field.url.lower()
        if url.endswith('.pdf'):
            return format_html('<a href="{}" target="_blank" rel="noopener" class="button" style="background:#dc3545; color:white; padding:5px 10px; border-radius:4px; text-decoration:none; white-space:nowrap;">View PDF</a>', file_field.url)
        elif url.endswith(('.png', '.jpg', '.jpeg')):
            label = "Image"
            if "passport" in obj.doc_type.lower(): label = "Photo"
            elif "signature" in obj.doc_type.lower(): label = "Signature"
            elif "thumb" in obj.doc_type.lower(): label = "Thumb"
            return format_html('<a href="{}" target="_blank" rel="noopener" title="{}"><img src="{}" style="max-height: 40px; border-radius: 4px; border:1px solid #ddd;"/></a>', file_field.url, label, file_field.url)
        return "-"
    document_preview.short_description = 'Preview'

    def validation_status(self, obj):
        canon_dt = obj.doc_type
        
        # PDFs and non-strict images get a pass automatically for now, or you can add specific PDF validation
        if obj.mime_type == 'application/pdf' or canon_dt not in ['passport_photo', 'signature', 'thumb_impression']:
            return "-"
            
        errors = []
        
        # 1. Format
        if not obj.mime_type or obj.mime_type not in ["image/jpeg", "image/jpg"]:
            errors.append(f"Format required: image/jpeg, got {obj.mime_type}")
            
        # 2. Size
        kb = obj.optimized_size_kb or obj.original_size_kb or 0
        if canon_dt == "passport_photo":
            if kb < 5 or kb > 50: errors.append(f"Size out of range: {kb} KB (required 5-50 KB)")
        else:
            if kb < 5 or kb > 20: errors.append(f"Size out of range: {kb} KB (required 5-20 KB)")
            
        # 3. Dimensions
        w, h = obj.image_width or 0, obj.image_height or 0
        if canon_dt == "passport_photo":
            if w != 132 or h != 170: errors.append(f"Wrong dimensions: {w}x{h} (required 132x170)")
        else:
            if w != 170 or h != 132: errors.append(f"Wrong dimensions: {w}x{h} (required 170x132)")
            
        # 4. DPI
        dpi_val = obj.actual_dpi
        if not dpi_val:
            errors.append("No DPI metadata found")
        else:
            try:
                x_dpi = int(dpi_val.split("x")[0].strip())
                if canon_dt == "passport_photo":
                    if x_dpi < 96 or x_dpi > 300: errors.append(f"DPI out of range: {x_dpi} (required 96-300)")
                else:
                    if x_dpi < 96 or x_dpi > 200: errors.append(f"DPI out of range: {x_dpi} (required 96-200)")
            except:
                errors.append("Invalid DPI metadata format")
                
        if errors:
            err_str = "\\n".join(errors)
            return format_html('<span style="color: red; font-weight: bold;" title="{}">FAIL</span>', err_str)
        
        return format_html('<span style="color: green; font-weight: bold;">PASS</span>')
    validation_status.short_description = "Validation"


@admin.register(StudentApplication)
class StudentApplicationAdmin(admin.ModelAdmin):
    list_select_related = ('program_opting', 'status', 'verification_status', 'state', 'district', 'country', 'religion', 'marital_status', 'community', 'ex_serviceman', 'occupation', 'qualification', 'year_of_study')
    list_per_page = 50
    
    list_display = (
        'application_number', 'passport_photo_preview', 'full_name', 'father_name', 'mother_name', 
        'dob', 'gender', 'religion_display', 'marital_status_display', 'community_display', 'ex_serviceman_display', 
        'occupation_display', 'masked_aadhaar', 'mobile_number', 'alternative_mobile', 'email', 
        'country_display', 'state_display', 'district_display', 'pincode', 'institution_display', 'qualification_display', 
        'year_of_study_display', 'program_display', 'registration_number', 'abc_id', 'hall_ticket_number', 
        'submission_date', 'status_badge', 'verification_badge'
    )
    
    list_filter = (
        'status', 'verification_status', 'gender', 'religion', 'community', 
        'occupation', 'qualification', 'marital_status', 'program_opting', 
        'submission_date', 'state', 'district'
    )
    
    autocomplete_fields = ('country', 'state', 'district')
    
    search_fields = (
        'application_number', 'full_name', 'aadhaar_number', 'mobile_number', 
        'registration_number', 'abc_id', 'institution'
    )
    
    date_hierarchy = 'submission_date'
    ordering = ('-submission_date',)
    
    inlines = [UploadedDocumentInline]
    
    readonly_fields = (
        'application_number', 'submission_date', 'last_updated', 
        'ip_address', 'browser_info', 'ack_pdf_link', 'ack_png_link', 'ack_jpg_link',
        'approved_by', 'approval_date'
    )
    
    fieldsets = (
        ('System Information', {
            'fields': (
                ('application_number', 'status', 'verification_status'),
                ('submission_date', 'last_updated'),
                ('ip_address', 'browser_info'),
            ),
            'classes': ('collapse',)
        }),
        ('Verification Section', {
            'fields': (
                'remarks', 'approved_by', 'approval_date'
            )
        }),
        ('Acknowledgement Files', {
            'fields': ('ack_pdf_link', 'ack_png_link', 'ack_jpg_link'),
            'description': "Server-generated acknowledgement card downloads."
        }),
        ('Personal Details', {
            'fields': (
                'full_name', 'father_name', 'mother_name', 
                'dob', 'gender', 'marital_status', 
                'religion', 'community', 'occupation', 'ex_serviceman',
                'aadhaar_number'
            )
        }),
        ('Contact Details', {
            'fields': (
                'mobile_number', 'alternative_mobile', 'email', 'communication_address', 
                'country', 'state', 'district', 'pincode'
            )
        }),
        ('Educational Details', {
            'fields': (
                'qualification', 'program_opting', 'year_of_study', 'institution', 
                'hall_ticket_number', 'registration_number', 'abc_id'
            )
        }),
    )

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if request.user.is_superuser:
            if 'masked_aadhaar' in list_display:
                idx = list_display.index('masked_aadhaar')
                list_display[idx] = 'aadhaar_number'
        return tuple(list_display)

    def get_readonly_fields(self, request, obj=None):
        ro_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            if 'masked_aadhaar' not in ro_fields:
                ro_fields.append('masked_aadhaar')
        return tuple(ro_fields)

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if not request.user.is_superuser:
            new_fieldsets = []
            for name, opts in fieldsets:
                if name == 'Personal Details':
                    fields = list(opts['fields'])
                    if 'aadhaar_number' in fields:
                        idx = fields.index('aadhaar_number')
                        fields[idx] = 'masked_aadhaar'
                    opts['fields'] = tuple(fields)
                new_fieldsets.append((name, opts))
            return tuple(new_fieldsets)
        return super().get_fieldsets(request, obj)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('documents')

    @admin.display(description="PHOTO")
    def passport_photo_preview(self, obj):
        doc = obj.documents.filter(doc_type__iexact='passport_photo').first()
        if doc and doc.compressed_file:
            url = doc.compressed_file.url
            return format_html('<a href="{}" target="_blank" style="white-space:nowrap;">View Photo</a>', url)
        return "-"

    def masked_aadhaar(self, obj):
        if obj.aadhaar_number and len(obj.aadhaar_number) == 12:
            return f"********{obj.aadhaar_number[-4:]}"
        return obj.aadhaar_number
    masked_aadhaar.short_description = "Aadhaar"

    def institution_display(self, obj):
        return obj.institution if obj.institution else "-"
    institution_display.short_description = 'Institution'
    
    def program_display(self, obj):
        return str(obj.program_opting) if obj.program_opting else "-"
    program_display.short_description = 'Program'

    @admin.display(description="Religion")
    def religion_display(self, obj): return str(obj.religion) if obj.religion else "-"

    @admin.display(description="Community")
    def community_display(self, obj): return str(obj.community) if obj.community else "-"

    @admin.display(description="Marital Status")
    def marital_status_display(self, obj): return str(obj.marital_status) if obj.marital_status else "-"

    @admin.display(description="Ex-Serviceman")
    def ex_serviceman_display(self, obj): return str(obj.ex_serviceman) if obj.ex_serviceman else "-"

    @admin.display(description="Occupation")
    def occupation_display(self, obj): return str(obj.occupation) if obj.occupation else "-"

    @admin.display(description="Country")
    def country_display(self, obj): return str(obj.country) if obj.country else "-"

    @admin.display(description="State")
    def state_display(self, obj): return str(obj.state) if obj.state else "-"

    @admin.display(description="District")
    def district_display(self, obj): return str(obj.district) if obj.district else "-"

    @admin.display(description="Qualification")
    def qualification_display(self, obj): return str(obj.qualification) if obj.qualification else "-"

    @admin.display(description="Year of Study")
    def year_of_study_display(self, obj): return str(obj.year_of_study) if obj.year_of_study else "-"

    def status_badge(self, obj):
        if not obj.status:
            return format_html('<span style="color: gray; font-weight: bold;">UNKNOWN</span>')
        color_map = {'PENDING': '#ffc107', 'APPROVED': '#198754', 'REJECTED': '#dc3545', 'CORRECTION': '#fd7e14'}
        bg_color = color_map.get(obj.status.code, '#6c757d')
        text_color = '#000' if bg_color == '#ffc107' else '#fff'
        return format_html('<span style="background-color: {}; color: {}; padding: 4px 8px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>', bg_color, text_color, obj.status.name)
    status_badge.short_description = 'Status'
    
    def verification_badge(self, obj):
        if not obj.verification_status:
            return "-"
        color_map = {'PENDING': '#ffc107', 'VERIFIED': '#198754', 'CORRECTION': '#fd7e14'}
        bg_color = color_map.get(obj.verification_status.code, '#6c757d')
        text_color = '#000' if bg_color == '#ffc107' else '#fff'
        return format_html('<span style="background-color: {}; color: {}; padding: 4px 8px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>', bg_color, text_color, obj.verification_status.name)
    verification_badge.short_description = 'Verification'
    
    actions = ['approve_applications', 'reject_applications', 'mark_verified', 'need_correction', 'export_excel', 'export_pdf', 'export_zip', 'download_documents']

    def approve_applications(self, request, queryset):
        approved_status = ApplicationStatus.objects.filter(code='APPROVED').first()
        if not approved_status:
            self.message_user(request, "Error: APPROVED status not found.", level=messages.ERROR)
            return
        updated = queryset.update(status=approved_status)
        self.message_user(request, f"{updated} applications approved.", level=messages.SUCCESS)
    approve_applications.short_description = "Approve Selected"
    
    def reject_applications(self, request, queryset):
        rejected_status = ApplicationStatus.objects.filter(code='REJECTED').first()
        if not rejected_status:
            self.message_user(request, "Error: REJECTED status not found.", level=messages.ERROR)
            return
        updated = queryset.update(status=rejected_status)
        self.message_user(request, f"{updated} applications rejected.", level=messages.WARNING)
    reject_applications.short_description = "Reject Selected"
    
    def mark_verified(self, request, queryset):
        verified_status = VerificationStatus.objects.filter(code='VERIFIED').first()
        if not verified_status:
            self.message_user(request, "Error: VERIFIED status not found.", level=messages.ERROR)
            return
        updated = queryset.update(verification_status=verified_status)
        self.message_user(request, f"{updated} applications marked as verified.", level=messages.SUCCESS)
    mark_verified.short_description = "Mark Verified"
    
    def need_correction(self, request, queryset):
        correction_status = VerificationStatus.objects.filter(code='CORRECTION').first()
        if not correction_status:
            self.message_user(request, "Error: CORRECTION status not found.", level=messages.ERROR)
            return
        updated = queryset.update(verification_status=correction_status)
        self.message_user(request, f"{updated} applications marked as need correction.", level=messages.SUCCESS)
    need_correction.short_description = "Need Correction"
    
    def export_excel(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="applications_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Application Number', 'Full Name', 'Aadhaar', 'Mobile', 'Email', 
            'State', 'District', 'Religion', 'Community', 'Marital Status',
            'Ex-Serviceman', 'Status', 'Verification Status', 'Submission Date'
        ])
        
        for app in queryset.select_related(
            'state', 'district', 'religion', 'community', 
            'marital_status', 'ex_serviceman', 'status', 'verification_status'
        ):
            writer.writerow([
                app.application_number,
                app.full_name,
                app.aadhaar_number,
                app.mobile_number,
                app.email,
                str(app.state) if app.state else '-',
                str(app.district) if app.district else '-',
                str(app.religion) if app.religion else '-',
                str(app.community) if app.community else '-',
                str(app.marital_status) if app.marital_status else '-',
                str(app.ex_serviceman) if app.ex_serviceman else '-',
                app.status.name if app.status else '-',
                app.verification_status.name if app.verification_status else '-',
                app.submission_date.strftime('%Y-%m-%d %H:%M:%S') if app.submission_date else '-'
            ])
            
        return response
    export_excel.short_description = "Export to CSV/Excel"

    def export_pdf(self, request, queryset):
        self.message_user(request, "PDF export initiated (Not fully implemented yet).", level=messages.INFO)
    export_pdf.short_description = "Export PDF"

    def export_zip(self, request, queryset):
        import zipfile
        import io
        import os
        from datetime import datetime
        from django.http import HttpResponse
        from utilities.export_helpers import generate_student_details_excel, generate_student_information_pdf
        from utilities.folder_manager import get_student_folder_name

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for app in queryset.prefetch_related('documents'):
                if app.storage_folder:
                    app_folder = f"{app.storage_folder}/"
                else:
                    try:
                        app_folder = f"{get_student_folder_name(app.aadhaar_number, app.full_name)}/"
                    except ValueError:
                        safe_name = str(app.full_name).replace(" ", "_")
                        aadhaar = app.aadhaar_number if app.aadhaar_number else "NoAadhaar"
                        app_folder = f"{aadhaar}_{safe_name}/"
                
                try:
                    excel_data = generate_student_details_excel(app)
                    zip_file.writestr(f"{app_folder}Student_Details.xlsx", excel_data)
                except Exception as e:
                    print(f"Error generating Excel for {app.application_number}: {e}")
                
                try:
                    pdf_data = generate_student_information_pdf(app)
                    zip_file.writestr(f"{app_folder}Student_Information.pdf", pdf_data)
                except Exception as e:
                    print(f"Error generating PDF for {app.application_number}: {e}")
                
                if app.acknowledgement_pdf and app.acknowledgement_pdf.name:
                    if os.path.exists(app.acknowledgement_pdf.path):
                        zip_file.write(app.acknowledgement_pdf.path, arcname=f"{app_folder}Acknowledgement.pdf")
                
                doc_folders = {
                    'passport_photo': 'Passport_Photo',
                    'signature': 'Signature',
                    'thumb_impression': 'Left_Thumb',
                    'aadhaar_pdf': 'Aadhaar',
                    'community_certificate': 'Community_Certificate',
                    'registration_screenshot': 'Registration_Screenshot',
                    'abc_screenshot': 'ABC_ID',
                    'supporting_documents': 'Supporting_Documents'
                }
                
                for doc in app.documents.all():
                    folder_name = doc_folders.get(doc.doc_type, doc.doc_type.capitalize())
                    
                    if doc.original_file and doc.original_file.name:
                        if os.path.exists(doc.original_file.path):
                            ext = doc.original_file.name.split('.')[-1]
                            zip_file.write(
                                doc.original_file.path, 
                                arcname=f"{app_folder}{folder_name}/original.{ext}"
                            )
                            
                    if doc.compressed_file and doc.compressed_file.name:
                        if os.path.exists(doc.compressed_file.path):
                            ext = doc.compressed_file.name.split('.')[-1]
                            zip_file.write(
                                doc.compressed_file.path, 
                                arcname=f"{app_folder}{folder_name}/optimized.{ext}"
                            )

        buffer.seek(0)
        date_str = datetime.now().strftime("%d-%m-%Y")
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="Student_Applications_{date_str}.zip"'
        return response
    export_zip.short_description = "Export ZIP"
    
    def download_documents(self, request, queryset):
        self.message_user(request, "Document download initiated (Not fully implemented yet).", level=messages.INFO)
    download_documents.short_description = "Download Documents"

    def ack_pdf_link(self, obj):
        if obj.acknowledgement_pdf:
            return format_html('<a href="{}" target="_blank" class="button" style="background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 4px;">Download PDF</a>', obj.acknowledgement_pdf.url)
        return "Not Generated"
    ack_pdf_link.short_description = "A4 PDF"

    def ack_png_link(self, obj):
        if obj.acknowledgement_png:
            return format_html('<a href="{}" target="_blank" class="button" style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px;">Download PNG</a>', obj.acknowledgement_png.url)
        return "Not Generated"
    ack_png_link.short_description = "High-Res PNG"

    def ack_jpg_link(self, obj):
        if obj.acknowledgement_jpg:
            return format_html('<a href="{}" target="_blank" class="button" style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px;">Download JPG</a>', obj.acknowledgement_jpg.url)
        return "Not Generated"
    ack_jpg_link.short_description = "High-Res JPG"

from django.contrib.admin.sites import AdminSite

original_get_app_list = AdminSite.get_app_list

def custom_get_app_list(self, request, app_label=None):
    app_list = original_get_app_list(self, request, app_label)
    app_order = {
        'auth': 1,
        'registrations': 2,
        'masterdata': 3,
    }
    app_list.sort(key=lambda x: app_order.get(x['app_label'], 999))
    return app_list

AdminSite.get_app_list = custom_get_app_list
'''

with codecs.open('registrations/admin.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
