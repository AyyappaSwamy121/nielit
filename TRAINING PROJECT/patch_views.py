import os

with open('registrations/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We will inject the DB save logic into auto_save_field
import re

# Find auto_save_field
auto_save_start = content.find('def auto_save_field(request):')
auto_save_end = content.find('def get_batch_code(request):')

old_auto_save = content[auto_save_start:auto_save_end]

new_auto_save = '''def auto_save_field(request):
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

'''

content = content.replace(old_auto_save, new_auto_save)

# Also update final_submit to use the draft app instead of creating a new one
final_submit_start = content.find('def final_submit(request):')
final_submit_end = content.find('def success_view(request):')
old_final_submit = content[final_submit_start:final_submit_end]

new_final_submit = '''def final_submit(request):
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
                    msg = f"A new application ({app.application_number}) has been submitted by {app.full_name}.\n\n"
                    msg += f"Mobile: {app.mobile_number}\nEmail: {app.email}\nStatus: Submitted\n\n"
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
            messages.error(request, 'An unexpected error occurred while saving your application. Please contact support.')
            return redirect('preview_application')
            
    return redirect('registration')

'''

content = content.replace(old_final_submit, new_final_submit)

with open('registrations/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("DB Draft Logic Patched!")
