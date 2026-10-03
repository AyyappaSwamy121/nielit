from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.db import transaction
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from registrations.models import StudentApplication, UploadedDocument
from registrations.forms import StudentApplicationForm
from masterdata.models import (
    Country, State, District, Religion, Qualification, Program, Occupation, 
    Community, MaritalStatus, ApplicationStatus, YearOfStudy, ExServiceStatus,
    TrainingPartner
)
from utilities.application_number import generate_application_number
from utilities.image_optimizer import process_and_optimize_image
from utilities.pdf_optimizer import compress_pdf
from utilities.acknowledgement_generator import generate_acknowledgement_files
from utilities.folder_manager import get_student_folder_name
from django.contrib import messages
import mimetypes
import os
import shutil
import logging
import traceback
import io
import zipfile
from django.utils.crypto import get_random_string

logger = logging.getLogger(__name__)

def registration_view(request):
    """
    Renders the public registration form.
    Pre-fills data if 'Back to Edit' was clicked from Preview.
    Loads dynamic dropdowns from Master Data.
    """
    context = {
        'countries': Country.objects.filter(is_active=True).order_by('display_order'),
        'states': State.objects.filter(is_active=True).order_by('display_order'),
        'districts': District.objects.filter(is_active=True).order_by('display_order'),
        'religions': Religion.objects.filter(is_active=True).order_by('display_order'),
        'marital_statuses': MaritalStatus.objects.filter(is_active=True).order_by('display_order'),
        'ex_services': ExServiceStatus.objects.filter(is_active=True).order_by('display_order'),
        'communities': Community.objects.filter(is_active=True).order_by('display_order'),
        'occupations': Occupation.objects.filter(is_active=True).order_by('display_order'),
        'qualifications': Qualification.objects.filter(is_active=True).order_by('display_order'),
        'programs': Program.objects.filter(is_active=True).order_by('display_order'),
        'training_partners': TrainingPartner.objects.filter(is_active=True).order_by('display_order'),
        'applying_qualification_choices': StudentApplication.APPLYING_QUALIFICATION_CHOICES,
        'mode_choices': StudentApplication.MODE_OF_QUALIFICATION_CHOICES,
        'status_choices': StudentApplication.COMPLETION_STATUS_CHOICES,
    }
    if request.GET.get('edit') != '1':
        if 'temp_application_data' in request.session:
            del request.session['temp_application_data']
        if 'temp_files' in request.session:
            del request.session['temp_files']
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', request.session.session_key or 'anon')
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        request.session.modified = True
    
    if 'temp_application_data' in request.session:
        temp_data = request.session['temp_application_data']
        # Fix existing invalid data in session
        import re
        modified = False
        for name_field in ['full_name', 'father_name', 'mother_name']:
            val = temp_data.get(name_field, '')
            if val and not re.match(r"^[a-zA-Z\s]+$", val):
                temp_data[name_field] = ''
                modified = True
        
        if modified:
            request.session['temp_application_data'] = temp_data
            request.session.modified = True
            
        context['form_data'] = temp_data
        
    if 'temp_files' in request.session:
        context['temp_files'] = request.session['temp_files']
    return render(request, 'registration/index.html', context)

def submit_application(request):
    """
    Step 1: Intercepts form submission via AJAX.
    Validates data, saves it to Django session, saves files to temp storage.
    Redirects to Preview upon success via JSON response.
    """
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json')
    
    if request.method == 'POST':
        try:
            # 1. Gather POST data
            form_data = {key: value for key, value in request.POST.items()}
            
            # Force Country to India ID in POST data before validation
            india = Country.objects.filter(name__iexact='india').first()
            if india:
                form_data['country'] = str(india.id)
                
            # 2. Handle File Uploads into Temp Storage FIRST (so they are preserved even if text validation fails)
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', request.session.session_key or 'anon')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            fs = FileSystemStorage(location=temp_dir)
            temp_files = request.session.get('temp_files', {})
            
            file_errors = {}
            
            for filename, file_obj in request.FILES.items():
                mime_type, _ = mimetypes.guess_type(file_obj.name)
                doc_type = filename.replace('upload_', '').capitalize()
                
                # specific validation for PDFs (Aadhaar, Community Certificate, Additional Documents)
                if doc_type in ['Aadhaar', 'Community_certificate', 'Additional_documents']:
                    if mime_type != 'application/pdf':
                        file_errors[filename] = [f'{doc_type.replace("_", " ")} must be a PDF file.']
                        continue
                    if file_obj.size > 2 * 1024 * 1024:
                        file_errors[filename] = [f'{doc_type.replace("_", " ")} exceeds maximum size of 2MB.']
                        continue
                
                if doc_type == 'File':
                    if mime_type not in ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']:
                        file_errors[filename] = ['Upload File must be PDF, JPG, JPEG, or PNG.']
                        continue
                    if file_obj.size > 2 * 1024 * 1024:
                        file_errors[filename] = ['Upload File exceeds maximum size of 2MB.']
                        continue
                
                # Normalize doc type strings
                if doc_type == 'Passport_photo': doc_type = 'Passport_Photo'
                elif doc_type == 'Left_thumb': doc_type = 'Left_Thumb'
                elif doc_type == 'Father_signature': doc_type = 'Father_Signature'
                elif doc_type == 'Additional_documents': doc_type = 'Additional_Documents'

                # Image Optimization
                if mime_type in ['image/jpeg', 'image/jpg', 'image/png'] or doc_type in ['Passport_Photo', 'Signature', 'Left_Thumb', 'Abc_id', 'Father_Signature']:
                    
                    processed = process_and_optimize_image(file_obj, doc_type)
                    
                    saved_orig = fs.save(f"orig_{file_obj.name}", processed['original_file'])
                    saved_comp = fs.save(f"opt_{file_obj.name}", processed['optimized_file'])
                    
                    temp_files[doc_type] = {
                        'original': os.path.join(temp_dir, saved_orig),
                        'compressed': os.path.join(temp_dir, saved_comp),
                        'url': f"{settings.MEDIA_URL}temp_uploads/{request.session.session_key or 'anon'}/{saved_comp}",
                        'filename': file_obj.name,
                        'size': f"{processed['optimized_file_size'] / 1024:.2f} KB",
                        'metadata': {
                            'original_file_size': processed['original_file_size'],
                            'optimized_file_size': processed['optimized_file_size'],
                            'image_width': processed['image_width'],
                            'image_height': processed['image_height'],
                            'mime_type': processed['mime_type'],
                            'compression_percentage': float(processed['compression_percentage'])
                        }
                    }
                else:
                    # Non-images (PDFs)
                    saved_name = fs.save(file_obj.name, file_obj)
                    compressed_name = f"compressed_{saved_name}"
                    if mime_type == 'application/pdf':
                        compressed = compress_pdf(fs.open(saved_name))
                        fs.save(compressed_name, compressed)
                    else:
                        shutil.copyfile(fs.path(saved_name), fs.path(compressed_name))
                        
                    temp_files[doc_type] = {
                        'original': os.path.join(temp_dir, saved_name),
                        'compressed': os.path.join(temp_dir, compressed_name),
                        'url': f"{settings.MEDIA_URL}temp_uploads/{request.session.session_key or 'anon'}/{compressed_name}",
                        'filename': file_obj.name,
                        'size': f"{file_obj.size / 1024:.2f} KB",
                        'metadata': None
                    }
                
            # Update session with successfully processed files
            request.session['temp_files'] = temp_files
            
            # Enforce Mandatory Uploads AFTER processing what was sent
            mandatory_uploads = ['upload_passport_photo', 'upload_signature', 'upload_left_thumb', 'upload_father_signature', 'upload_aadhaar', 'upload_community_certificate', 'upload_additional_documents']
            uploaded_keys = request.FILES.keys()
            for mu in mandatory_uploads:
                if mu not in uploaded_keys and mu.replace('upload_', '').capitalize() not in temp_files and mu.replace('upload_', '').title().replace(' ', '_') not in temp_files:
                    if mu == 'upload_passport_photo' and 'Passport_Photo' in temp_files: continue
                    if mu == 'upload_left_thumb' and 'Left_Thumb' in temp_files: continue
                    if mu == 'upload_father_signature' and 'Father_Signature' in temp_files: continue
                    if mu == 'upload_additional_documents' and 'Additional_Documents' in temp_files: continue
                    if mu not in file_errors:
                        file_errors[mu] = [f'Missing mandatory upload: {mu.replace("upload_", "").replace("_", " ").title()}']
            
            # 3. Validate Form Text Fields
            form = StudentApplicationForm(data=form_data)
            all_errors = {}
            if not form.is_valid():
                all_errors.update(form.errors)
            if file_errors:
                all_errors.update(file_errors)
                
            if all_errors:
                if is_ajax:
                    return JsonResponse({"success": False, "errors": all_errors})
                else:
                    for field, errors in all_errors.items():
                        for error in errors:
                            messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                    return redirect('/?edit=1')
                    
            # 4. If all validations pass
            request.session['temp_application_data'] = form_data
            
            if is_ajax:
                from django.urls import reverse
                return JsonResponse({"success": True, "redirect_url": reverse('preview_application')})
            return redirect('preview_application')
            
        except Exception as e:
            logger.exception("Error during submit_application")
            if is_ajax:
                return JsonResponse({
                    "success": False,
                    "errors": {"__all__": ["We were unable to process the uploaded files due to a server error. Please try again, and contact support if the issue persists."]}
                })
            messages.error(request, 'We were unable to process the uploaded files due to a server error. Please try again, and contact support if the issue persists.')
            return redirect('/?edit=1')
            
    if is_ajax:
        return JsonResponse({"success": False, "errors": {"__all__": ["Invalid request method."]}})
    messages.error(request, 'Invalid request method.')
    return redirect('registration')

def preview_application(request):
    """
    Step 2: Render the Preview Page using Session Data.
    """
    if 'temp_application_data' not in request.session:
        return redirect('registration')
        
    data = request.session['temp_application_data']
    files = request.session.get('temp_files', {})
    
    # Mask Aadhaar
    aadhaar = data.get('aadhaar_number', '')
    masked_aadhaar = f"********{aadhaar[-4:]}" if len(aadhaar) >= 4 else aadhaar

    # Resolve Foreign Keys to readable string representations
    display_data = {}
    
    def get_name(model_class, id_val):
        if not id_val: return "-"
        obj = model_class.objects.filter(id=id_val).first()
        return str(obj) if obj else "-"

    display_data['country'] = get_name(Country, data.get('country'))
    display_data['state'] = get_name(State, data.get('state'))
    
    # District returns name (State name), which is fine, but we just want string.
    district_obj = District.objects.filter(id=data.get('district')).first()
    display_data['district'] = district_obj.name if district_obj else "-"
    
    display_data['religion'] = get_name(Religion, data.get('religion'))
    display_data['marital_status'] = get_name(MaritalStatus, data.get('marital_status'))
    display_data['community'] = get_name(Community, data.get('community'))
    display_data['occupation'] = get_name(Occupation, data.get('occupation'))
    display_data['qualification'] = get_name(Qualification, data.get('qualification'))
    if display_data['qualification'] == 'Other' and data.get('custom_stream'):
        display_data['qualification'] = f"Other ({data.get('custom_stream')})"
        
    display_data['applying_qualification'] = dict(StudentApplication.APPLYING_QUALIFICATION_CHOICES).get(data.get('applying_qualification'), "-")
    display_data['program_opting'] = get_name(Program, data.get('program_opting'))
    display_data['mode_of_qualification'] = dict(StudentApplication.MODE_OF_QUALIFICATION_CHOICES).get(data.get('mode_of_qualification'), "-")
    display_data['completion_status'] = dict(StudentApplication.COMPLETION_STATUS_CHOICES).get(data.get('completion_status'), "-")
    display_data['training_partner'] = get_name(TrainingPartner, data.get('training_partner'))
    
    display_data['ex_serviceman'] = get_name(ExServiceStatus, data.get('ex_serviceman'))
    
    context = {
        'data': data,
        'display_data': display_data,
        'files': files,
        'masked_aadhaar': masked_aadhaar
    }
    return render(request, 'registration/preview.html', context)

def final_submit(request):
    """
    Step 3: Finalize submission.
    Transfer from Session & Temp Storage to SQLite & Permanent Media Storage.
    Generate Application Number and clear session.
    """
    if request.method == 'POST' and 'temp_application_data' in request.session:
        data = request.session['temp_application_data']
        files = request.session.get('temp_files', {})
        
        # Secondary Validation against bypassed requests
        form = StudentApplicationForm(data=data)
        if not form.is_valid():
            messages.error(request, 'Validation failed. Please start over.')
            return redirect('registration')
        
        try:
            with transaction.atomic():
                app_no = generate_application_number()
                
                # Fetch FKs
                country = Country.objects.filter(id=data.get('country')).first()
                state = State.objects.filter(id=data.get('state')).first()
                district = District.objects.filter(id=data.get('district')).first()
                religion = Religion.objects.filter(id=data.get('religion')).first()
                marital = MaritalStatus.objects.filter(id=data.get('marital_status')).first()
                community = Community.objects.filter(id=data.get('community')).first()
                occupation = Occupation.objects.filter(id=data.get('occupation')).first()
                qualification = Qualification.objects.filter(id=data.get('qualification')).first()
                year = YearOfStudy.objects.filter(id=data.get('year_of_study')).first()
                program = Program.objects.filter(id=data.get('program_opting')).first()
                ex_service = ExServiceStatus.objects.filter(id=data.get('ex_serviceman')).first()
                status = ApplicationStatus.objects.filter(code='PENDING').first()
                
                aadhaar_num = data.get('aadhaar_number', '')
                full_nm = data.get('full_name', '')
                storage_folder_name = get_student_folder_name(aadhaar_num, full_nm)
                
                # Update existing DB Draft or create new
                app_id = request.session.get('draft_app_id')
                if app_id:
                    app = StudentApplication.objects.filter(id=app_id).first()
                else:
                    app = StudentApplication()
                    
                app.application_number = app_no
                app.storage_folder = storage_folder_name
                app.full_name = data.get('full_name', '')
                app.father_name = data.get('father_name', '')
                app.mother_name = data.get('mother_name', '')
                app.dob = data.get('dob')
                app.gender = data.get('gender', '')
                app.religion = religion
                app.marital_status = marital
                app.community = community
                app.ex_serviceman = ex_service
                app.occupation = occupation
                app.mobile_number = data.get('mobile_number', '')
                app.alternative_mobile = data.get('alternative_mobile', '')
                app.email = data.get('email', '')
                app.communication_address = data.get('communication_address', '')
                app.country = country
                app.state = state
                app.district = district
                app.pincode = data.get('pincode', '')
                app.institution = data.get('institution', '')
                app.hall_ticket_number = data.get('hall_ticket_number', '')
                app.registration_number = data.get('registration_number', '')
                app.qualification = qualification
                app.year_of_study = year
                app.program_opting = program
                app.aadhaar_number = data.get('aadhaar_number', '')
                app.abc_id = data.get('abc_id', '')
                app.distinguishing_mark = data.get('distinguishing_mark', '')
                app.status = status
                app.ip_address = request.META.get('REMOTE_ADDR')
                app.save()
                
                # Move files from temp to permanent
                for doc_type, file_info in files.items():
                    # Check if already exists for this draft
                    doc = UploadedDocument.objects.filter(application=app, doc_type=doc_type).first()
                    if not doc:
                        doc = UploadedDocument(application=app, doc_type=doc_type)
                    
                    if file_info.get('metadata'):
                        meta = file_info['metadata']
                        doc.original_file_size = meta['original_file_size']
                        doc.optimized_file_size = meta['optimized_file_size']
                        doc.image_width = meta['image_width']
                        doc.image_height = meta['image_height']
                        doc.mime_type = meta['mime_type']
                        doc.compression_percentage = meta['compression_percentage']
                        if 'jpeg_quality' in meta:
                            doc.jpeg_quality = meta['jpeg_quality']
                        if 'validation_status' in meta:
                            doc.validation_status = meta['validation_status']
                        if 'processing_policy' in meta:
                            doc.processing_policy = meta['processing_policy']
                    
                    from django.core.files import File
                    if os.path.exists(file_info['original']):
                        with open(file_info['original'], 'rb') as f:
                            doc.original_file.save('original.jpg' if file_info.get('metadata') else file_info['filename'], File(f), save=False)
                    if os.path.exists(file_info['compressed']):
                        with open(file_info['compressed'], 'rb') as f:
                            doc.compressed_file.save('optimized.jpg' if file_info.get('metadata') else f"compressed_{file_info['filename']}", File(f), save=False)
                            
                    doc.save()
                    
                # Clean up session and temp dir
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', request.session.session_key or 'anon')
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    
                del request.session['temp_application_data']
                if 'temp_files' in request.session:
                    del request.session['temp_files']
                if 'draft_app_id' in request.session:
                    del request.session['draft_app_id']
                    
                # Generate Acknowledgement files
                generate_acknowledgement_files(app)
                
                # Send Email Notification
                from django.core.mail import send_mail
                from django.urls import reverse
                admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')
                try:
                    admin_url = request.build_absolute_uri(f"/dashboard/applications/")
                    msg = f"A new application ({app.application_number}) has been submitted by {app.full_name}.\\n\\n"
                    msg += f"Mobile: {app.mobile_number}\\nEmail: {app.email}\\nStatus: Submitted\\n\\n"
                    msg += f"View details here: {admin_url}"
                    send_mail(
                        f"New Application Submitted: {app.application_number}",
                        msg,
                        settings.DEFAULT_FROM_EMAIL,
                        [admin_email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.error(f"Failed to send admin email: {e}")
                
                request.session['success_data'] = {
                    'app_id': app.id,
                    'app_no': app_no,
                    'name': app.full_name,
                    'date': app.submission_date.strftime('%Y-%m-%d %H:%M:%S') if app.submission_date else '',
                    'pdf_url': app.acknowledgement_pdf.url if app.acknowledgement_pdf else '',
                    'png_url': app.acknowledgement_png.url if app.acknowledgement_png else '',
                    'jpg_url': app.acknowledgement_jpg.url if app.acknowledgement_jpg else '',
                    'auth_token': get_random_string(32),
                }
                
                return redirect('success')
                
        except Exception as e:
            logger.exception("Error during final_submit")
            messages.error(request, 'We encountered an error while saving your application. Please try again, and contact support if the problem continues.')
            return redirect('preview_application')
            
    return redirect('registration')

def success_view(request):
    """
    Step 4: Render Success Page.
    """
    if 'success_data' not in request.session:
        return redirect('registration')
        
    data = request.session['success_data']
    
    app = get_object_or_404(StudentApplication, id=data['app_id'])
    documents = UploadedDocument.objects.filter(application=app).order_by('id')
    
    return render(request, 'registration/success.html', {
        'data': data,
        'documents': documents,
        'auth_token': data['auth_token'],
    })

def download_document(request, token, doc_id):
    success_data = request.session.get('success_data')
    if not success_data or success_data.get('auth_token') != token:
        raise Http404("Unauthorized or expired session.")
        
    doc = get_object_or_404(UploadedDocument, id=doc_id, application_id=success_data['app_id'])
    
    is_view = request.GET.get('view') == '1'
    
    file_to_send = doc.compressed_file if doc.compressed_file else doc.original_file
    
    if is_view and doc.processing_policy == 'document_preserve' and doc.original_file:
        file_to_send = doc.original_file
    
    if not file_to_send or not os.path.exists(file_to_send.path):
        raise Http404("File not found.")
        
    response = FileResponse(file_to_send.open('rb'))
    if is_view:
        filename = doc.original_filename if file_to_send == doc.original_file else doc.compressed_filename
        response['Content-Disposition'] = f'inline; filename="{filename}"'
    else:
        filename = doc.compressed_filename or doc.original_filename
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
    response['Cache-Control'] = 'no-store, private'
    return response

def download_all_documents(request, token):
    success_data = request.session.get('success_data')
    if not success_data or success_data.get('auth_token') != token:
        raise Http404("Unauthorized or expired session.")
        
    app = get_object_or_404(StudentApplication, id=success_data['app_id'])
    documents = UploadedDocument.objects.filter(application=app)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for doc in documents:
            file_to_send = doc.compressed_file if doc.compressed_file else doc.original_file
            if file_to_send and os.path.exists(file_to_send.path):
                # We save with original doc_type as name to avoid collisions
                ext = os.path.splitext(file_to_send.name)[1]
                zip_file.write(file_to_send.path, f"{doc.doc_type}{ext}")
                
    zip_buffer.seek(0)
    response = FileResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="Processed_Documents_{app.application_number}.zip"'
    return response

def check_duplicate(request):
    field = request.GET.get('field')
    value = request.GET.get('value')
    allowed_fields = ['aadhaar_number', 'mobile_number', 'email', 'abc_id', 'registration_number', 'hall_ticket_number']
    if field in allowed_fields and value:
        exists = StudentApplication.objects.filter(**{field: value}).exists()
        return JsonResponse({'exists': exists, 'field': field})
    return JsonResponse({'error': 'Invalid parameters'}, status=400)

def get_states(request):
    country_id = request.GET.get('country_id')
    states = list(State.objects.filter(country_id=country_id, is_active=True).order_by('display_order').values('id', 'name'))
    return JsonResponse(states, safe=False)

def get_districts(request):
    state_id = request.GET.get('state_id')
    districts = list(District.objects.filter(state_id=state_id, is_active=True).order_by('display_order').values('id', 'name'))
    return JsonResponse(districts, safe=False)

def auto_save_field(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        field = request.POST.get('field')
        value = request.POST.get('value')
        
        if field:
            import re
            if field in ['full_name', 'father_name', 'mother_name']:
                if value and not re.match(r"^[a-zA-Z\s]+$", value):
                    return JsonResponse({'success': False, 'message': 'Only alphabets and spaces are allowed.'})
                if value:
                    value = value.strip()
            elif field == 'distinguishing_mark':
                if value:
                    value = value.strip()
                    if len(value) < 5 or len(value) > 100:
                        return JsonResponse({'success': False, 'message': 'Must be between 5 and 100 characters.'})
                    if not re.match(r"^[a-zA-Z\s]+$", value):
                        return JsonResponse({'success': False, 'message': 'Only alphabetic characters and spaces are allowed.'})
            elif field == 'mobile_number':
                if not value or not re.match(r"^[6-9]\d{9}$", value):
                    return JsonResponse({'success': False, 'message': 'Enter a valid 10-digit mobile number.'})
            elif field == 'alternative_mobile':
                if value and not re.match(r"^\d{10}$", value):
                    return JsonResponse({'success': False, 'message': 'Enter a valid 10-digit mobile number.'})
            elif field == 'aadhaar_number':
                if not value or not re.match(r"^\d{12}$", value):
                    return JsonResponse({'success': False, 'message': 'Enter a valid 12-digit Aadhaar number.'})
            elif field == 'pincode':
                if not value or not re.match(r"^\d{6}$", value):
                    return JsonResponse({'success': False, 'message': 'Enter a valid 6-digit pincode.'})
            elif field == 'email':
                if value and not re.match(r"[^@]+@[^@]+\.[^@]+", value):
                    return JsonResponse({'success': False, 'message': 'Enter a valid email address.'})
            elif field == 'abc_id':
                if not value or not re.match(r"^\d{12}$", value):
                    return JsonResponse({'success': False, 'message': 'Enter a valid 12-digit ABC ID (Apaar ID).'})
            elif field == 'percentage':
                if value:
                    try:
                        val = float(value)
                        if val < 0 or val > 100:
                            return JsonResponse({'success': False, 'message': 'Enter a valid percentage between 0 and 100.'})
                    except ValueError:
                        return JsonResponse({'success': False, 'message': 'Enter a valid percentage between 0 and 100.'})
            elif field == 'custom_stream':
                if value:
                    if len(value) < 3 or len(value) > 100:
                        return JsonResponse({'success': False, 'message': 'Must be between 3 and 100 characters.'})
                    if not re.match(r"^[A-Za-z0-9\s\-\/&\(\)]+$", value):
                        return JsonResponse({'success': False, 'message': 'Contains invalid characters.'})
            
            temp_data = request.session.get('temp_application_data', {})
            temp_data[field] = value
            
            # Cross-field validation check before saving
            if field in ['completion_status', 'year_of_passing', 'percentage']:
                status = temp_data.get('completion_status')
                yop = temp_data.get('year_of_passing')
                pct = temp_data.get('percentage')
                
                import datetime
                current_year = datetime.datetime.now().year
                
                if status == 'Completed':
                    if yop and int(yop) > current_year:
                        if field == 'year_of_passing': return JsonResponse({'success': False, 'message': 'Year cannot be greater than current year.'})
                    if not pct and field == 'percentage':
                        return JsonResponse({'success': False, 'message': 'Percentage is mandatory for Completed status.'})
                elif status == 'Ongoing':
                    if yop and int(yop) < current_year:
                        if field == 'year_of_passing': return JsonResponse({'success': False, 'message': 'Year cannot be less than current year.'})
            
            request.session['temp_application_data'] = temp_data
            request.session.modified = True
            
            # --- DB SAVE AS SOURCE OF TRUTH ---
            app_id = request.session.get('draft_app_id')
            if app_id:
                app = StudentApplication.objects.filter(id=app_id).first()
            else:
                app = None
                
            if not app:
                status_obj, _ = ApplicationStatus.objects.get_or_create(code='INCOMPLETE', defaults={'name': 'Incomplete'})
                app = StudentApplication.objects.create(status=status_obj)
                request.session['draft_app_id'] = app.id
                
            try:
                db_val = value if value != "" else None
                if field == 'country' and db_val: db_val = Country.objects.filter(id=db_val).first()
                elif field == 'state' and db_val: db_val = State.objects.filter(id=db_val).first()
                elif field == 'district' and db_val: db_val = District.objects.filter(id=db_val).first()
                elif field == 'religion' and db_val: db_val = Religion.objects.filter(id=db_val).first()
                elif field == 'marital_status' and db_val: db_val = MaritalStatus.objects.filter(id=db_val).first()
                elif field == 'community' and db_val: db_val = Community.objects.filter(id=db_val).first()
                elif field == 'occupation' and db_val: db_val = Occupation.objects.filter(id=db_val).first()
                elif field == 'qualification' and db_val: db_val = Qualification.objects.filter(id=db_val).first()
                elif field == 'program_opting' and db_val: db_val = Program.objects.filter(id=db_val).first()
                elif field == 'training_partner' and db_val: db_val = TrainingPartner.objects.filter(id=db_val).first()
                elif field == 'ex_serviceman' and db_val: db_val = ExServiceStatus.objects.filter(id=db_val).first()
                
                if hasattr(app, field):
                    setattr(app, field, db_val)
                    app.save(update_fields=[field])
            except Exception as e:
                logger.error(f"DB Draft save error for {field}: {e}")
                
            return JsonResponse({'success': True, 'message': '? Already saved'})
    return JsonResponse({'success': False})

def get_batch_code(request):
    training_partner_id = request.GET.get('training_partner_id')
    if training_partner_id:
        from masterdata.models import BatchCode
        batch = BatchCode.objects.filter(training_partner_id=training_partner_id).first()
        if batch:
            return JsonResponse({'success': True, 'batch_code': batch.code})
    return JsonResponse({'success': False, 'message': 'No batch assigned. Please contact the administrator.'})

import urllib.request
import json
import re
from django.core.cache import cache

def pincode_lookup(request):
    pincode = request.GET.get('pincode', '').strip()
    if not re.match(r"^\d{6}$", pincode):
        return JsonResponse({'success': False, 'message': 'Invalid PIN Code. Please enter a valid Indian PIN Code.'})
    
    cache_key = f"pincode_{pincode}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        state_name, district_name = cached_data
    else:
        try:
            url = f"https://api.postalpincode.in/pincode/{pincode}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                if not data or data[0].get('Status') != 'Success' or not data[0].get('PostOffice'):
                    return JsonResponse({'success': False, 'message': 'Invalid PIN Code. Please enter a valid Indian PIN Code.'})
                
                post_office = data[0]['PostOffice'][0]
                state_name = post_office.get('State')
                district_name = post_office.get('District')
                
                if not state_name or not district_name:
                    return JsonResponse({'success': False, 'message': 'Invalid PIN Code. Please enter a valid Indian PIN Code.'})
                    
                cache.set(cache_key, (state_name, district_name), 86400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Failed to fetch PIN Code data. Please select manually.'})
            
    # Get or create country (India)
    country, _ = Country.objects.get_or_create(name__iexact='India', defaults={'name': 'India', 'code': 'IN', 'iso_code': 'IND'})
    
    # Look up or create state and district
    state_qs = State.objects.filter(name__iexact=state_name)
    if state_qs.exists():
        state = state_qs.first()
    else:
        state = State.objects.create(name=state_name, code=state_name.upper()[:10], country=country)
        
    district_qs = District.objects.filter(name__iexact=district_name, state=state)
    if district_qs.exists():
        district = district_qs.first()
    else:
        district = District.objects.create(name=district_name, code=district_name.upper()[:10], state=state)
        
    # Save to session
    temp_data = request.session.get('temp_application_data', {})
    temp_data['pincode'] = pincode
    temp_data['state'] = str(state.id)
    temp_data['district'] = str(district.id)
    request.session['temp_application_data'] = temp_data
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'state_id': state.id,
        'district_id': district.id,
        'message': '✓ Already saved'
    })

def async_upload_pdf(request):
    if request.method == 'POST' and request.FILES:
        file_key = list(request.FILES.keys())[0]
        file_obj = request.FILES[file_key]
        doc_type = file_key.replace('upload_', '').capitalize()
        if doc_type == 'Additional_documents': doc_type = 'Additional_Documents'

        mime_type, _ = mimetypes.guess_type(file_obj.name)
        if mime_type != 'application/pdf':
            return JsonResponse({'success': False, 'error': 'Must be a PDF file.'})

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', request.session.session_key or 'anon')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        fs = FileSystemStorage(location=temp_dir)
        saved_name = fs.save(file_obj.name, file_obj)
        
        if file_obj.size > 2 * 1024 * 1024:
            compressed = compress_pdf(fs.open(saved_name))
            compressed_name = f"compressed_{saved_name}"
            fs.save(compressed_name, compressed)
            
            final_size = fs.size(compressed_name)
            if final_size > 2 * 1024 * 1024:
                fs.delete(saved_name)
                fs.delete(compressed_name)
                return JsonResponse({'success': False, 'error': 'Unable to compress this PDF below 2 MB. Please upload a smaller PDF.'})
            
            fs.delete(saved_name)
            final_url = f"{settings.MEDIA_URL}temp_uploads/{request.session.session_key or 'anon'}/{compressed_name}"
            final_path_original = os.path.join(temp_dir, compressed_name)
            final_path_compressed = os.path.join(temp_dir, compressed_name)
            final_size_bytes = final_size
        else:
            compressed_name = f"compressed_{saved_name}"
            shutil.copyfile(fs.path(saved_name), fs.path(compressed_name))
            final_url = f"{settings.MEDIA_URL}temp_uploads/{request.session.session_key or 'anon'}/{compressed_name}"
            final_path_original = os.path.join(temp_dir, saved_name)
            final_path_compressed = os.path.join(temp_dir, compressed_name)
            final_size_bytes = file_obj.size
            
        temp_files = request.session.get('temp_files', {})
        temp_files[doc_type] = {
            'original': final_path_original,
            'compressed': final_path_compressed,
            'url': final_url,
            'filename': file_obj.name,
            'size': f"{final_size_bytes / 1024 / 1024:.2f} MB" if final_size_bytes > 1024*1024 else f"{final_size_bytes / 1024:.2f} KB",
            'metadata': None
        }
        request.session['temp_files'] = temp_files
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'filename': file_obj.name,
            'size': temp_files[doc_type]['size'],
            'url': final_url
        })
        
    return JsonResponse({'success': False, 'error': 'Invalid request'})
