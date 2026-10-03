from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from registrations.models import StudentApplication, UploadedDocument, SUBMITTED_STATUS_CODES
from registrations.forms import StudentApplicationForm
from dashboard.form_config_service import FormConfigurationService
from masterdata.models import (
    Country, State, District, Religion, Qualification, Program, Occupation, 
    Community, MaritalStatus, ApplicationStatus, YearOfStudy, ExServiceStatus,
    TrainingPartner, EducationalInstitution
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

def resolve_fk(model_class, value):
    if not value:
        return None
    try:
        return model_class.objects.filter(id=value).first()
    except (ValueError, TypeError):
        return None

def get_name(model_class, id_val):
    if not id_val:
        return "-"
    obj = model_class.objects.filter(id=id_val).first()
    return str(obj) if obj else "-"

def app_to_form_data(app):
    """Convert a StudentApplication model instance into form_data dict for pre-filling."""
    d = {}
    simple_fields = [
        'full_name', 'father_name', 'mother_name', 'dob', 'gender',
        'nationality', 'physically_handicapped', 'annual_income',
        'mobile_number', 'alternative_mobile', 'email', 'communication_address',
        'pincode', 'area_village_name', 'institution', 'hall_ticket_number',
        'registration_number', 'nielit_registration_number', 'applying_qualification', 'custom_stream',
        'mode_of_qualification', 'completion_status', 'percentage',
        'year_of_passing', 'batch_code', 'aadhaar_number', 'abc_id',
        'distinguishing_mark',
    ]
    for f in simple_fields:
        v = getattr(app, f, '')
        if v is None:
            d[f] = ''
        elif hasattr(v, 'strftime'):
            d[f] = v.strftime('%Y-%m-%d')
        elif isinstance(v, (int, float, bool, str)):
            d[f] = v
        else:
            d[f] = str(v)
    d['consent_given'] = bool(app.consent_given)
    fk_fields = {
        'country': 'country_id', 'state': 'state_id', 'district': 'district_id',
        'religion': 'religion_id', 'marital_status': 'marital_status_id',
        'community': 'community_id', 'occupation': 'occupation_id',
        'qualification': 'qualification_id', 'program_opting': 'program_opting_id',
        'training_partner': 'training_partner_id', 'ex_serviceman': 'ex_serviceman_id',
    }
    for key, attr in fk_fields.items():
        v = getattr(app, attr, None)
        d[key] = str(v) if v else ''
    return d

def populate_app_from_data(app, cleaned):
    """Map validated form cleaned_data onto a StudentApplication instance."""
    app.full_name = cleaned.get('full_name', '')
    app.father_name = cleaned.get('father_name', '')
    app.mother_name = cleaned.get('mother_name', '')
    app.dob = cleaned.get('dob')
    app.gender = cleaned.get('gender', '')
    app.religion = cleaned.get('religion')
    app.marital_status = cleaned.get('marital_status')
    app.community = cleaned.get('community')
    app.ex_serviceman = cleaned.get('ex_serviceman')
    app.occupation = cleaned.get('occupation')
    app.nationality = cleaned.get('nationality', 'Indian')
    app.physically_handicapped = cleaned.get('physically_handicapped', 'No')
    app.annual_income = cleaned.get('annual_income') or 0
    app.mobile_number = cleaned.get('mobile_number', '')
    app.alternative_mobile = cleaned.get('alternative_mobile', '')
    app.email = cleaned.get('email', '')
    app.communication_address = cleaned.get('communication_address', '')
    app.country = cleaned.get('country')
    app.state = cleaned.get('state')
    app.district = cleaned.get('district')
    app.pincode = cleaned.get('pincode', '')
    app.area_village_name = cleaned.get('area_village_name', '')
    app.institution = cleaned.get('institution', '')
    app.hall_ticket_number = cleaned.get('hall_ticket_number', '')
    app.registration_number = cleaned.get('registration_number', '')
    app.nielit_registration_number = cleaned.get('nielit_registration_number', '')
    app.applying_qualification = cleaned.get('applying_qualification', '12th or equivalent')
    app.qualification = cleaned.get('qualification')
    app.custom_stream = cleaned.get('custom_stream', '')
    app.mode_of_qualification = cleaned.get('mode_of_qualification', 'Full Time')
    app.completion_status = cleaned.get('completion_status', 'Completed')
    app.percentage = cleaned.get('percentage')
    app.year_of_passing = cleaned.get('year_of_passing')
    app.training_partner = cleaned.get('training_partner')
    app.batch_code = cleaned.get('batch_code', '')
    app.program_opting = cleaned.get('program_opting')
    app.aadhaar_number = cleaned.get('aadhaar_number', '')
    app.abc_id = cleaned.get('abc_id', '')
    app.distinguishing_mark = cleaned.get('distinguishing_mark', '')
    app.consent_given = bool(cleaned.get('consent_given'))
    return app

def save_documents_to_db(app, files):
    """Persist processed temp files as UploadedDocument records (idempotent by doc_type)."""
    from django.core.files import File
    for doc_type, file_info in files.items():
        doc = UploadedDocument.objects.filter(application=app, doc_type=doc_type).first()
        if not doc:
            doc = UploadedDocument(application=app, doc_type=doc_type)
        if file_info.get('metadata'):
            meta = file_info['metadata']
            doc.original_file_size = meta.get('original_file_size')
            doc.optimized_file_size = meta.get('optimized_file_size')
            doc.image_width = meta.get('image_width')
            doc.image_height = meta.get('image_height')
            doc.mime_type = meta.get('mime_type')
            doc.compression_percentage = meta.get('compression_percentage')
            if 'jpeg_quality' in meta:
                doc.jpeg_quality = meta['jpeg_quality']
            if 'validation_status' in meta:
                doc.validation_status = meta['validation_status']
            if 'processing_policy' in meta:
                doc.processing_policy = meta['processing_policy']
        if file_info.get('original') and os.path.exists(file_info['original']):
            with open(file_info['original'], 'rb') as f:
                doc.original_file.save('original.jpg' if file_info.get('metadata') else file_info['filename'], File(f), save=False)
        if file_info.get('compressed') and os.path.exists(file_info['compressed']):
            with open(file_info['compressed'], 'rb') as f:
                doc.compressed_file.save('optimized.jpg' if file_info.get('metadata') else f"compressed_{file_info['filename']}", File(f), save=False)
        doc.save()

def build_preview_context(app, files=None):
    """Build the preview template context from a DB-backed StudentApplication."""
    display_data = {}
    display_data['country'] = str(app.country) if app.country else "-"
    display_data['state'] = str(app.state) if app.state else "-"
    display_data['district'] = str(app.district) if app.district else "-"
    display_data['religion'] = str(app.religion) if app.religion else "-"
    display_data['marital_status'] = str(app.marital_status) if app.marital_status else "-"
    display_data['community'] = str(app.community) if app.community else "-"
    display_data['occupation'] = str(app.occupation) if app.occupation else "-"
    display_data['qualification'] = str(app.qualification) if app.qualification else "-"
    if app.qualification and str(app.qualification) == 'Other' and app.custom_stream:
        display_data['qualification'] = f"Other ({app.custom_stream})"
    display_data['applying_qualification'] = dict(StudentApplication.APPLYING_QUALIFICATION_CHOICES).get(app.applying_qualification, app.applying_qualification or "-")
    display_data['program_opting'] = str(app.program_opting) if app.program_opting else "-"
    display_data['mode_of_qualification'] = dict(StudentApplication.MODE_OF_QUALIFICATION_CHOICES).get(app.mode_of_qualification, app.mode_of_qualification or "-")
    display_data['completion_status'] = dict(StudentApplication.COMPLETION_STATUS_CHOICES).get(app.completion_status, app.completion_status or "-")
    display_data['training_partner'] = str(app.training_partner) if app.training_partner else "-"
    display_data['ex_serviceman'] = str(app.ex_serviceman) if app.ex_serviceman else "-"
    display_data['area_village_name'] = app.area_village_name or "-"

    docs = UploadedDocument.objects.filter(application=app).order_by('doc_type')
    db_documents = {}
    for doc in docs:
        db_documents[doc.doc_type] = {
            'filename': doc.original_filename,
            'file_url': doc.original_file.url if doc.original_file else None,
            'has_file': True,
        }

    document_sections = []
    for doc_type, label, is_pdf in [
        ('Passport_Photo', 'Passport Size Photograph', False),
        ('Signature', 'Signature', False),
        ('Aadhaar', 'Aadhaar Card', True),
        ('Left_Thumb', 'Thumb Impression', False),
        ('Abc_id', 'Appari Id (ABC Id)', False),
        ('Father_Signature', "Father's/Guardian's Signature", False),
        ('Community_certificate', 'Community Certificate', True),
        ('Additional_Documents', 'Additional Documents', True),
    ]:
        db = db_documents.get(doc_type)
        document_sections.append({
            'doc_type': doc_type,
            'label': label,
            'is_pdf': is_pdf,
            'uploaded': bool(db and db.get('file_url')),
            'filename': db['filename'] if db else '',
            'file_url': db['file_url'] if db else '',
        })

    aadhaar = app.aadhaar_number or ''
    masked_aadhaar = f"********{aadhaar[-4:]}" if len(aadhaar) >= 4 else aadhaar

    data = {
        'full_name': app.full_name,
        'father_name': app.father_name,
        'mother_name': app.mother_name,
        'dob': app.dob,
        'gender': app.gender,
        'mobile_number': app.mobile_number,
        'alternative_mobile': app.alternative_mobile,
        'email': app.email,
        'communication_address': app.communication_address,
        'aadhaar_number': app.aadhaar_number,
        'abc_id': app.abc_id,
        'distinguishing_mark': app.distinguishing_mark,
        'pincode': app.pincode,
        'area_village_name': app.area_village_name,
        'institution': app.institution,
        'hall_ticket_number': app.hall_ticket_number,
        'registration_number': app.registration_number,
        'nielit_registration_number': app.nielit_registration_number,
        'applying_qualification': app.applying_qualification,
        'mode_of_qualification': app.mode_of_qualification,
        'completion_status': app.completion_status,
        'percentage': app.percentage,
        'year_of_passing': app.year_of_passing,
        'batch_code': app.batch_code,
        'custom_stream': app.custom_stream,
        'consent_given': app.consent_given,
    }

    return {
        'data': data,
        'display_data': display_data,
        'db_documents': db_documents,
        'document_sections': document_sections,
        'masked_aadhaar': masked_aadhaar,
        'app': app,
        'files': files or {},
    }

def get_qualification_category(name):
    name_lower = name.lower().strip()
    
    # Exact matches that go to 'Other' (must be checked before substring matches)
    if name_lower in ['diploma', 'degree', 'other', 'ph.d', 'phd']:
        return 'Other'
    
    # 1. 12th / Equivalent
    if '12th' in name_lower or 'equivalent' in name_lower:
        return '12th / Equivalent'
        
    # 2. Diploma (prefix match — e.g. "Diploma in ..." or "2yrs of 3 yr dip...")
    if name_lower.startswith('diploma in') or '2yrs of 3 yr dip' in name_lower:
        return 'Diploma'
        
    # 3. Postgraduate
    if any(name_lower.startswith(p) for p in ['m.tech', 'm.sc', 'mba', 'mca', 'm.com', 'ma ', 'm.pharmacy', 'm.ed', 'llm']):
        return 'Postgraduate'
    # Exact matches for postgraduate
    if name_lower in ['ma', 'mba', 'mca', 'llm']:
        return 'Postgraduate'
        
    # 4. B.Tech / Engineering
    if name_lower.startswith('b.tech') or 'engineering' in name_lower:
        return 'B.Tech / Engineering'
        
    # 5. B.Sc
    if name_lower.startswith('b.sc'):
        return 'B.Sc'
        
    # 6. Other Bachelor's Degrees
    if any(name_lower.startswith(p) for p in ['b.com', 'bba', 'ba', 'bsw', 'bca', 'mbbs', 'bds', 'b.pharmacy', 'nursing', 'physiotherapy', 'llb', 'b.ed']):
        return "Other Bachelor's Degrees"
        
    return 'Other'

def registration_view(request):
    """
    Renders the public registration form or landing page.
    - Initial visit (no app_id, no prefill, no draft): shows landing page with "Find Your Registration" card
    - After search/continue (app_id, prefill_aadhaar, prefill_email, resumed): shows full registration form
    """
    import json
    from registrations.models import UploadedDocument

    # Determine if this is an initial visit (show landing page) or form visit
    has_app_id = bool(request.GET.get('app_id') or request.session.get('draft_app_id'))
    has_prefill = bool(request.GET.get('prefill_aadhaar') or request.GET.get('prefill_email'))
    has_resumed = request.GET.get('resumed') == '1'
    has_edit = request.GET.get('edit') == '1'
    has_new = request.GET.get('new') == '1'
    has_reset = request.GET.get('reset') == '1'
    has_section = bool(request.GET.get('section'))
    has_temp_data = bool(request.session.get('temp_application_data'))

    # Show landing page only on initial visit with no parameters indicating form context
    is_initial_visit = not (has_app_id or has_prefill or has_resumed or has_edit or has_new or has_reset or has_section or has_temp_data)

    if is_initial_visit:
        # Clear any stale session data for a fresh start
        for key in ['temp_application_data', 'temp_files', 'draft_app_id', 'completed_sections', 'active_section']:
            if key in request.session:
                del request.session[key]
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', request.session.session_key or 'anon')
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        request.session.modified = True

        return render(request, 'registration/landing.html')

    # --- FULL REGISTRATION FORM LOGIC (existing) ---
    
    qualifications = Qualification.objects.filter(is_active=True).order_by('display_order')
    qualifications_list = []
    
    grouped_qualifications = {
        '12th / Equivalent': [],
        'Diploma': [],
        'B.Tech / Engineering': [],
        'B.Sc': [],
        "Other Bachelor's Degrees": [],
        'Postgraduate': [],
        'Other': []
    }
    
    for q in qualifications:
        category = get_qualification_category(q.name)
        qualifications_list.append({
            'id': q.id,
            'name': q.name,
            'category': category
        })
        if category in grouped_qualifications:
            grouped_qualifications[category].append(q)
        else:
            grouped_qualifications['Other'].append(q)
    
    context = {
        'countries': Country.objects.filter(is_active=True).order_by('display_order'),
        'states': State.objects.filter(is_active=True).order_by('display_order'),
        'districts': District.objects.filter(is_active=True).order_by('display_order'),
        'religions': Religion.objects.filter(is_active=True).order_by('display_order'),
        'marital_statuses': MaritalStatus.objects.filter(is_active=True).order_by('display_order'),
        'communities': Community.objects.filter(is_active=True).order_by('display_order'),
        'occupations': Occupation.objects.filter(is_active=True).order_by('display_order'),
        'ex_services': ExServiceStatus.objects.filter(is_active=True).order_by('display_order'),
        'qualifications': qualifications,
        'grouped_qualifications': grouped_qualifications,
        'qualifications_json': json.dumps(qualifications_list),
        'programs': Program.objects.filter(is_active=True).order_by('display_order'),
        'training_partners': TrainingPartner.objects.filter(is_active=True).order_by('display_order'),
        'educational_institutions': EducationalInstitution.objects.filter(is_active=True).order_by('name'),
        'applying_qualification_choices': StudentApplication.APPLYING_QUALIFICATION_CHOICES,
        'mode_choices': StudentApplication.MODE_OF_QUALIFICATION_CHOICES,
        'status_choices': StudentApplication.COMPLETION_STATUS_CHOICES,
    }
    
    # Check for existing application and its uploaded documents
    app_id = request.GET.get('app_id') or request.session.get('draft_app_id')
    db_documents = {}
    if app_id:
        app = StudentApplication.objects.filter(id=app_id).first()
        if app:
            docs = UploadedDocument.objects.filter(application=app).order_by('doc_type')
            for doc in docs:
                db_documents[doc.doc_type] = {
                    'filename': doc.original_filename,
                    'file_url': doc.original_file.url if doc.original_file else None,
                    'has_file': True
                }
    
    context['db_documents'] = db_documents
    
    # Only reset temporary state if explicitly requested via query parameter
    if request.GET.get('reset') == '1' or request.GET.get('new') == '1':
        for key in ['temp_application_data', 'temp_files', 'draft_app_id', 'completed_sections', 'active_section']:
            if key in request.session:
                del request.session[key]
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', request.session.session_key or 'anon')
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        request.session.modified = True
    
    # Load draft application from DB if available
    prefill_app = None
    app_id = request.GET.get('app_id') or request.session.get('draft_app_id')
    if app_id:
        prefill_app = StudentApplication.objects.filter(id=app_id).first()
        if prefill_app and prefill_app.is_submitted:
            prefill_app = None
            if 'draft_app_id' in request.session:
                del request.session['draft_app_id']

    if prefill_app:
        context['form_data'] = app_to_form_data(prefill_app)
    else:
        context.setdefault('form_data', {})

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
        
        context['form_data'].update(temp_data)
    
    if request.GET.get('resumed') == '1':
        context['resumed_banner'] = True
    if request.GET.get('prefill_aadhaar'):
        context['form_data']['aadhaar_number'] = request.GET.get('prefill_aadhaar')
    if request.GET.get('prefill_email'):
        context['form_data']['email'] = request.GET.get('prefill_email')
    if 'temp_files' in request.session:
        context['temp_files'] = request.session['temp_files']
    
    # Calculate completed sections from session and persisted draft data
    completed_sections = list(request.session.get('completed_sections', []))
    fd = context.get('form_data', {})

    # Step 1: Personal Details completion check
    has_step1 = bool(
        fd.get('full_name') and fd.get('dob') and fd.get('gender') and
        fd.get('father_name') and fd.get('mother_name')
    )
    if has_step1 and 'personal-details' not in completed_sections:
        completed_sections.append('personal-details')

    # Step 2: Contact Details completion check
    has_step2 = bool(
        has_step1 and fd.get('mobile_number') and fd.get('aadhaar_number') and
        fd.get('email') and fd.get('communication_address') and
        fd.get('state') and fd.get('district')
    )
    if has_step2 and 'contact-details' not in completed_sections:
        completed_sections.append('contact-details')

    # Step 3: Education Details completion check
    has_step3 = bool(
        has_step2 and fd.get('qualification') and fd.get('applying_qualification') and
        fd.get('institution') and fd.get('hall_ticket_number') and
        fd.get('mode_of_qualification') and fd.get('completion_status') and
        fd.get('year_of_passing') and fd.get('program_opting')
    )
    if has_step3 and 'education-details' not in completed_sections:
        completed_sections.append('education-details')

    request.session['completed_sections'] = completed_sections
    context['completed_sections'] = completed_sections
    context['completed_sections_json'] = json.dumps(completed_sections)

    # Determine initial active section
    requested_section = request.GET.get('section')
    if requested_section in ['personal-details', 'contact-details', 'education-details', 'document-uploads']:
        active_section = requested_section
    elif request.GET.get('edit') == '1':
        active_section = 'personal-details'
    elif 'education-details' in completed_sections:
        active_section = 'document-uploads'
    elif 'contact-details' in completed_sections:
        active_section = 'education-details'
    elif 'personal-details' in completed_sections:
        active_section = 'contact-details'
    else:
        active_section = 'personal-details'

    context['active_section'] = active_section

    # Form Builder: database is the single source of truth for rendering.
    known_inst_names = {i.name for i in context['educational_institutions']}
    current_inst = context['form_data'].get('institution') or ''
    context['is_other_institution'] = bool(current_inst and current_inst not in known_inst_names)
    fb_service = FormConfigurationService()
    fb_ctx = fb_service.preview_context()
    context['fb_sections'] = fb_ctx['fb_sections']
    active_slugs = {s.slug for s in fb_service.get_sections(active_only=True)}
    context['fb_section_visible_personal'] = 'personal-details' in active_slugs
    context['fb_section_visible_contact'] = 'contact-details' in active_slugs
    context['fb_section_visible_education'] = 'education-details' in active_slugs
    context['fb_section_visible_documents'] = 'document-uploads' in active_slugs
    context['fb_section_visible_declaration'] = 'declaration' in active_slugs
    context['fb_section_visible_additional'] = 'additional-documents' in active_slugs
    context['fb_field_visible'] = {
        f.field_name: f.visible
        for entry in fb_ctx['fb_sections']
        for f in entry['fields']
    }
    
    return render(request, 'registration/index.html', context)

def save_section(request):
    """
    Validates and temporarily saves an individual form section (Step 1, 2, or 3).
    Ensures sequential completion and updates draft StudentApplication in DB and session.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'errors': {'__all__': ['Invalid request method.']}}, status=405)

    section = request.POST.get('section', '').strip()
    if section not in ['personal-details', 'contact-details', 'education-details']:
        return JsonResponse({'success': False, 'errors': {'__all__': ['Invalid section requested.']}}, status=400)

    form_data = {key: value.strip() if isinstance(value, str) else value for key, value in request.POST.items()}
    
    # Handle country and institution mappings
    india = Country.objects.filter(name__iexact='india').first()
    if india:
        form_data['country'] = str(india.id)
    if form_data.get('institution') == 'Other' and form_data.get('other_institution'):
        form_data['institution'] = form_data['other_institution'].strip()
    if 'annual_income' in form_data and form_data['annual_income']:
        import re
        form_data['annual_income'] = re.sub(r'[^0-9]', '', str(form_data['annual_income']))

    errors = {}

    # Get or create draft application
    app_id = request.session.get('draft_app_id')
    app = None
    if app_id:
        app = StudentApplication.objects.filter(id=app_id).first()
        if app and app.is_submitted:
            app = None
    if not app:
        status_obj, _ = ApplicationStatus.objects.get_or_create(code='INCOMPLETE', defaults={'name': 'Incomplete'})
        app = StudentApplication(status=status_obj, application_number=f"DRAFT-{get_random_string(8)}")
        app.save()
        request.session['draft_app_id'] = app.id

    def check_dupe(field, val):
        if not val:
            return False
        qs = StudentApplication.objects.filter(
            **{field: val}, status__code__in=SUBMITTED_STATUS_CODES
        )
        if app and app.pk:
            qs = qs.exclude(pk=app.pk)
        return qs.exists()

    import datetime
    import re

    # 1. SECTION-SPECIFIC BUSINESS VALIDATION
    if section == 'personal-details':
        # Full Name
        name = form_data.get('full_name', '')
        if not name:
            errors['full_name'] = ['Full Name is required.']
        elif len(name) < 2:
            errors['full_name'] = ['Name must be at least 2 characters long.']
        elif len(name) > 150:
            errors['full_name'] = ['Name cannot exceed 150 characters.']
        elif not re.match(r"^[A-Za-z\s]+$", name):
            errors['full_name'] = ['Only alphabets and spaces are allowed. Numbers and special characters are not permitted.']

        # Father's Name
        father = form_data.get('father_name', '')
        if not father:
            errors['father_name'] = ["Father's Name is required."]
        elif len(father) < 2:
            errors['father_name'] = ['Name must be at least 2 characters long.']
        elif len(father) > 150:
            errors['father_name'] = ['Name cannot exceed 150 characters.']
        elif not re.match(r"^[A-Za-z\s]+$", father):
            errors['father_name'] = ['Only alphabets and spaces are allowed. Numbers and special characters are not permitted.']

        # Mother's Name
        mother = form_data.get('mother_name', '')
        if not mother:
            errors['mother_name'] = ["Mother's Name is required."]
        elif len(mother) < 2:
            errors['mother_name'] = ['Name must be at least 2 characters long.']
        elif len(mother) > 150:
            errors['mother_name'] = ['Name cannot exceed 150 characters.']
        elif not re.match(r"^[A-Za-z\s]+$", mother):
            errors['mother_name'] = ['Only alphabets and spaces are allowed. Numbers and special characters are not permitted.']

        # Date of Birth
        dob_str = form_data.get('dob', '')
        if not dob_str:
            errors['dob'] = ['Date of Birth is required.']
        else:
            try:
                dob = datetime.date.fromisoformat(dob_str)
                today = datetime.date.today()
                if dob > today:
                    errors['dob'] = ['Date of Birth cannot be in the future.']
                else:
                    min_age_date = today - datetime.timedelta(days=365 * 10)
                    if dob > min_age_date:
                        errors['dob'] = ['You must be at least 10 years old.']
            except ValueError:
                errors['dob'] = ['Enter a valid date of birth.']

        # Gender
        gender = form_data.get('gender', '')
        if not gender or gender not in ['Male', 'Female', 'Other']:
            errors['gender'] = ['Gender is required.']

        # Nationality
        nationality = form_data.get('nationality', '')
        if not nationality:
            errors['nationality'] = ['Nationality is required.']

        # Annual Income
        income_str = form_data.get('annual_income', '')
        if income_str:
            try:
                inc = int(income_str)
                if inc < 0:
                    errors['annual_income'] = ['Please enter a valid annual income.']
            except ValueError:
                errors['annual_income'] = ['Please enter a valid annual income.']

    elif section == 'contact-details':
        # Mobile Number
        mobile = form_data.get('mobile_number', '')
        if not mobile:
            errors['mobile_number'] = ['Mobile number is required.']
        elif not re.match(r"^[1-9]\d{9}$", mobile):
            errors['mobile_number'] = ['Number must be 10 digits and cannot start with 0.']
        elif check_dupe('mobile_number', mobile):
            errors['mobile_number'] = ['Student application with this Mobile number already exists.']

        # Aadhaar Number
        aadhaar = form_data.get('aadhaar_number', '')
        if not aadhaar:
            errors['aadhaar_number'] = ['Aadhaar number is required.']
        elif not re.match(r"^[1-9]\d{11}$", aadhaar):
            errors['aadhaar_number'] = ['Aadhaar number must be 12 digits and cannot start with 0.']
        elif check_dupe('aadhaar_number', aadhaar):
            errors['aadhaar_number'] = ['Student application with this Aadhaar number already exists.']

        # Alternative Mobile
        alt_mobile = form_data.get('alternative_mobile', '')
        if alt_mobile:
            if not re.match(r"^[1-9]\d{9}$", alt_mobile):
                errors['alternative_mobile'] = ['Number must be 10 digits and cannot start with 0.']
            elif alt_mobile == mobile:
                errors['alternative_mobile'] = ['Alternative mobile number cannot be the same as the primary mobile number.']

        # Email
        email = form_data.get('email', '')
        if not email:
            errors['email'] = ['Email is required.']
        elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors['email'] = ['Enter a valid email address.']
        elif check_dupe('email', email):
            errors['email'] = ['Student application with this Email already exists.']

        # Communication Address
        addr = form_data.get('communication_address', '')
        if not addr:
            errors['communication_address'] = ['Communication address is required.']
        elif len(addr) < 10:
            errors['communication_address'] = ['Address must be at least 10 characters long.']

        # Country
        country_id = form_data.get('country', '')
        if not country_id:
            errors['country'] = ['Country is required.']

        # State
        state_id = form_data.get('state', '')
        if not state_id:
            errors['state'] = ['State is required.']

        # District
        district_id = form_data.get('district', '')
        if not district_id:
            errors['district'] = ['District is required.']
        elif state_id:
            if not District.objects.filter(id=district_id, state_id=state_id).exists():
                errors['district'] = ['Selected District does not belong to the selected State.']

        # Pincode
        pincode = form_data.get('pincode', '')
        if pincode and not re.match(r"^\d{6}$", pincode):
            errors['pincode'] = ['Enter a valid 6-digit pincode.']

        # Area / Village Name
        area = form_data.get('area_village_name', '')
        if area and (len(area) < 2 or len(area) > 255):
            errors['area_village_name'] = ['Area/Village name must be between 2 and 255 characters.']

    elif section == 'education-details':
        # Applying Qualification
        app_qual = form_data.get('applying_qualification', '')
        if not app_qual:
            errors['applying_qualification'] = ['Applying qualification is required.']

        # Mode of Qualification
        mode = form_data.get('mode_of_qualification', '')
        if not mode:
            errors['mode_of_qualification'] = ['Mode of qualification is required.']

        # Completion Status
        comp_status = form_data.get('completion_status', '')
        if not comp_status:
            errors['completion_status'] = ['Completion status is required.']

        # Stream of Qualification (qualification)
        qual_id = form_data.get('qualification', '')
        if not qual_id:
            errors['qualification'] = ['Stream of qualification is required.']

        # Custom Stream
        stream = form_data.get('custom_stream', '')
        if stream:
            if len(stream) < 2 or len(stream) > 100:
                errors['custom_stream'] = ['Stream must be between 2 and 100 characters.']
            elif not re.match(r"^[A-Za-z0-9\s\-\/&\(\)]+$", stream):
                errors['custom_stream'] = ['Contains invalid characters.']

        # Year of Passing
        yop_str = form_data.get('year_of_passing', '')
        current_year = datetime.datetime.now().year
        yop = None
        if not yop_str:
            errors['year_of_passing'] = ['Year of passing is required.']
        else:
            try:
                yop = int(yop_str)
                if yop < 1950 or yop > current_year + 5:
                    errors['year_of_passing'] = [f'Year of passing must be between 1950 and {current_year + 5}.']
                elif comp_status == 'Completed' and yop > current_year:
                    errors['year_of_passing'] = ['Year cannot be greater than current year for Completed status.']
                elif comp_status == 'Ongoing' and yop < current_year:
                    errors['year_of_passing'] = ['Year cannot be less than current year for Ongoing status.']
            except ValueError:
                errors['year_of_passing'] = ['Enter a valid year of passing.']

        # Percentage
        pct_str = form_data.get('percentage', '')
        if comp_status == 'Completed':
            if not pct_str:
                errors['percentage'] = ['Percentage is mandatory for Completed status.']
            else:
                try:
                    pct = float(pct_str)
                    if pct < 0 or pct > 100:
                        errors['percentage'] = ['Enter a valid percentage between 0 and 100.']
                except ValueError:
                    errors['percentage'] = ['Enter a valid percentage between 0 and 100.']
        elif pct_str:
            try:
                pct = float(pct_str)
                if pct < 0 or pct > 100:
                    errors['percentage'] = ['Enter a valid percentage between 0 and 100.']
            except ValueError:
                errors['percentage'] = ['Enter a valid percentage between 0 and 100.']

        # Program Opting
        prog_id = form_data.get('program_opting', '')
        if not prog_id:
            errors['program_opting'] = ['Program opting is required.']

        # Institution
        inst = form_data.get('institution', '')
        if not inst or inst == 'Other':
            errors['institution'] = ['Please enter your educational institution name.']
        elif len(inst) < 3:
            errors['institution'] = ['Institution name must be at least 3 characters long.']
        elif len(inst) > 200:
            errors['institution'] = ['Institution name cannot exceed 200 characters.']
        else:
            inst_obj = EducationalInstitution.get_or_create_institution(inst)
            if inst_obj:
                form_data['institution'] = inst_obj.name

        # Hall Ticket Number
        ht = form_data.get('hall_ticket_number', '')
        if not ht:
            errors['hall_ticket_number'] = ['Hall ticket number is required.']
        elif len(ht) > 50:
            errors['hall_ticket_number'] = ['Hall ticket number cannot exceed 50 characters.']

        # Registration Number (sync from hall ticket if missing)
        reg_num = form_data.get('registration_number', '') or ht
        form_data['registration_number'] = reg_num

        # ABC ID
        abc = form_data.get('abc_id', '')
        if abc:
            if not re.match(r"^\d{12}$", abc):
                errors['abc_id'] = ['Enter a valid 12-digit ABC ID (Apaar ID).']
            elif check_dupe('abc_id', abc):
                errors['abc_id'] = ['Student application with this ABC ID already exists.']

        # NIELIT Registration Number
        nielit_reg = form_data.get('nielit_registration_number', '')
        if nielit_reg:
            if len(nielit_reg) > 50:
                errors['nielit_registration_number'] = ['NIELIT Registration Number cannot exceed 50 characters.']
            elif not re.match(r"^[A-Za-z0-9 -]*$", nielit_reg):
                errors['nielit_registration_number'] = ['Only letters, numbers, spaces, and hyphens (-) are allowed.']

    # 2. RUN FORM CONFIGURATION SERVICE VALIDATION ON SECTION FIELDS
    try:
        fb_service = FormConfigurationService()
        for field_config in fb_service.get_fields(visible_only=True):
            if field_config.section and field_config.section.slug == section:
                if field_config.field_type == 'file':
                    continue
                f_val = form_data.get(field_config.field_name, '')
                fb_errs = fb_service.validate_value(field_config, f_val)
                if fb_errs:
                    if field_config.field_name in errors:
                        for e in fb_errs:
                            if e not in errors[field_config.field_name]:
                                errors[field_config.field_name].append(e)
                    else:
                        errors[field_config.field_name] = fb_errs
    except Exception:
        logger.exception("Form configuration validation failed in save_section")

    if errors:
        return JsonResponse({'success': False, 'errors': errors})

    # 3. PERSIST SECTION DATA TO DRAFT APPLICATION AND SESSION
    temp_data = request.session.get('temp_application_data', {})
    temp_data.update(form_data)
    request.session['temp_application_data'] = temp_data

    # Map fields onto draft StudentApplication
    if section == 'personal-details':
        app.full_name = form_data.get('full_name', '')
        app.father_name = form_data.get('father_name', '')
        app.mother_name = form_data.get('mother_name', '')
        if form_data.get('dob'):
            try:
                app.dob = datetime.date.fromisoformat(form_data['dob'])
            except ValueError:
                pass
        app.gender = form_data.get('gender', '')
        app.nationality = form_data.get('nationality', 'Indian')
        app.physically_handicapped = form_data.get('physically_handicapped', 'No')
        app.annual_income = int(form_data.get('annual_income') or 0)
        app.religion = resolve_fk(Religion, form_data.get('religion'))
        app.marital_status = resolve_fk(MaritalStatus, form_data.get('marital_status'))
        app.community = resolve_fk(Community, form_data.get('community'))
        app.ex_serviceman = resolve_fk(ExServiceStatus, form_data.get('ex_serviceman'))
        next_section = 'contact-details'

    elif section == 'contact-details':
        app.mobile_number = form_data.get('mobile_number', '')
        app.alternative_mobile = form_data.get('alternative_mobile', '')
        app.email = form_data.get('email', '')
        app.aadhaar_number = form_data.get('aadhaar_number', '')
        app.communication_address = form_data.get('communication_address', '')
        app.country = resolve_fk(Country, form_data.get('country'))
        app.state = resolve_fk(State, form_data.get('state'))
        app.district = resolve_fk(District, form_data.get('district'))
        app.pincode = form_data.get('pincode', '')
        app.area_village_name = form_data.get('area_village_name', '')
        app.occupation = resolve_fk(Occupation, form_data.get('occupation'))
        next_section = 'education-details'

    elif section == 'education-details':
        app.applying_qualification = form_data.get('applying_qualification', '12th or equivalent')
        app.mode_of_qualification = form_data.get('mode_of_qualification', 'Full Time')
        app.completion_status = form_data.get('completion_status', 'Completed')
        app.qualification = resolve_fk(Qualification, form_data.get('qualification'))
        app.custom_stream = form_data.get('custom_stream', '')
        if form_data.get('percentage'):
            try:
                app.percentage = float(form_data['percentage'])
            except ValueError:
                pass
        if form_data.get('year_of_passing'):
            try:
                app.year_of_passing = int(form_data['year_of_passing'])
            except ValueError:
                pass
        app.program_opting = resolve_fk(Program, form_data.get('program_opting'))
        app.training_partner = resolve_fk(TrainingPartner, form_data.get('training_partner'))
        app.batch_code = form_data.get('batch_code', '')
        app.institution = form_data.get('institution', '')
        app.hall_ticket_number = form_data.get('hall_ticket_number', '')
        app.registration_number = form_data.get('registration_number', '')
        app.abc_id = form_data.get('abc_id', '')
        app.nielit_registration_number = form_data.get('nielit_registration_number', '')
        next_section = 'document-uploads'

    app.save()

    completed = list(request.session.get('completed_sections', []))
    if section not in completed:
        completed.append(section)
    request.session['completed_sections'] = completed
    request.session['draft_app_id'] = app.id
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'message': 'Section saved successfully.',
        'completed_sections': completed,
        'next_section': next_section
    })

def submit_application(request):
    """
    Step 1: Intercepts form submission via AJAX.
    Validates data, saves it to Django session, saves files to temp storage.
    Redirects to Preview upon success via JSON response.
    """
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json')
    
    if request.method == 'POST':
        print(f"SAVE PREVIEW VIEW CALLED - AJAX: {is_ajax}")
        try:
            # 1. Gather POST data
            form_data = {key: value for key, value in request.POST.items()}
            
            # Force Country to India ID in POST data before validation
            india = Country.objects.filter(name__iexact='india').first()
            if india:
                form_data['country'] = str(india.id)

            # If user selected Other, map the entered custom institution into institution
            if form_data.get('institution') == 'Other' and form_data.get('other_institution'):
                form_data['institution'] = form_data['other_institution'].strip()
            
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
                        file_errors[filename] = [{
                            'category': 'file_type',
                            'file_name': file_obj.name,
                            'message': f'{doc_type.replace("_", " ")} must be a PDF file.',
                            'allowed': ['PDF']
                        }]
                        continue
                    if file_obj.size > 2 * 1024 * 1024:
                        file_errors[filename] = [{
                            'category': 'file_size',
                            'file_name': file_obj.name,
                            'message': f'{doc_type.replace("_", " ")} exceeds maximum size of 2 MB.',
                            'current_size_kb': round(file_obj.size / 1024, 1),
                            'required_kb': 2048
                        }]
                        continue

                if doc_type == 'File':
                    if mime_type not in ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']:
                        file_errors[filename] = [{
                            'category': 'file_type',
                            'file_name': file_obj.name,
                            'message': 'Upload File must be PDF, JPG, JPEG, or PNG.',
                            'allowed': ['PDF','JPG','JPEG','PNG']
                        }]
                        continue
                    if file_obj.size > 2 * 1024 * 1024:
                        file_errors[filename] = [{
                            'category': 'file_size',
                            'file_name': file_obj.name,
                            'message': 'Upload File exceeds maximum size of 2 MB.',
                            'current_size_kb': round(file_obj.size / 1024,1),
                            'required_kb': 2048
                        }]
                        continue

                # Normalize doc type strings
                if doc_type == 'Passport_photo': doc_type = 'Passport_Photo'
                elif doc_type == 'Left_thumb': doc_type = 'Left_Thumb'
                elif doc_type == 'Father_signature': doc_type = 'Father_Signature'
                elif doc_type == 'Additional_documents': doc_type = 'Additional_Documents'

                # Image Optimization
                if mime_type in ['image/jpeg', 'image/jpg', 'image/png'] or doc_type in ['Passport_Photo', 'Signature', 'Left_Thumb', 'Abc_id', 'Father_Signature']:
                    try:
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
                    except Exception as e:
                        # Log and provide a structured, safe message for the frontend
                        logger.exception(f"Image processing failed for {file_obj.name}")
                        file_errors[filename] = [{
                            'category': 'processing_error',
                            'file_name': file_obj.name,
                            'message': 'The image could not be processed. Please try a different image or adjust the file.',
                            'hint': 'Allowed formats: JPG, JPEG, PNG. Max size: 2 MB.'
                        }]
                        continue
                else:
                    # Non-images (PDFs)
                    try:
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
                    except Exception as e:
                        logger.exception(f"PDF processing failed for {file_obj.name}")
                        file_errors[filename] = [{
                            'category': 'pdf_processing_error',
                            'file_name': file_obj.name,
                            'message': 'The uploaded PDF appears to be invalid or could not be processed.',
                            'hint': 'Please upload a valid, uncorrupted PDF file.'
                        }]
                        continue
            
            # Update session with successfully processed files
            request.session['temp_files'] = temp_files
            request.session.modified = True
            
            # Enforce Mandatory Uploads AFTER processing what was sent
            mandatory_uploads = ['upload_passport_photo', 'upload_signature', 'upload_left_thumb', 'upload_father_signature', 'upload_aadhaar', 'upload_community_certificate']
            uploaded_keys = request.FILES.keys()
            for mu in mandatory_uploads:
                if mu not in uploaded_keys and mu.replace('upload_', '').capitalize() not in temp_files and mu.replace('upload_', '').title().replace(' ', '_') not in temp_files:
                    if mu == 'upload_passport_photo' and 'Passport_Photo' in temp_files: continue
                    if mu == 'upload_left_thumb' and 'Left_Thumb' in temp_files: continue
                    if mu == 'upload_father_signature' and 'Father_Signature' in temp_files: continue
                    # 'upload_additional_documents' is optional now; no special-case check required
                    if mu not in file_errors:
                        file_errors[mu] = [{
                            'category': 'missing_upload',
                            'file_name': mu.replace('upload_', '').replace('_', ' ').title(),
                            'message': f'Missing mandatory upload: {mu.replace("upload_", "").replace("_", " ").title()}'
                        }]
            
            # 3. Validate Form Text Fields
            form = StudentApplicationForm(data=form_data)
            all_errors = {}
            if not form.is_valid():
                all_errors.update(form.errors)
            if file_errors:
                all_errors.update(file_errors)

            # 3b. Dynamic DB-driven validation (Form Builder).
            # The database configuration is the source of truth for field
            # requirements and rules. Errors are merged additively so the
            # existing hardcoded form logic is never bypassed or weakened.
            try:
                fb_service = FormConfigurationService()
                config_errors = {}
                for f in fb_service.get_visible_fields():
                    if f.field_type == 'file':
                        continue
                    errs = fb_service.validate_value(f, form_data.get(f.field_name, ''))
                    if errs:
                        config_errors[f.field_name] = errs
                for fname, fobj in request.FILES.items():
                    field = fb_service.get_field(fname)
                    if field:
                        errs = fb_service.validate_file(field, fobj)
                        if errs:
                            config_errors[fname] = errs
                for fname, errs in config_errors.items():
                    if fname in all_errors:
                        for e in errs:
                            if e not in all_errors[fname]:
                                all_errors[fname].append(e)
                    else:
                        all_errors[fname] = errs
            except Exception:
                # Never let config validation break submission.
                logger.exception("Error during form-builder validation")

            if all_errors:
                if is_ajax:
                    return JsonResponse({"success": False, "errors": all_errors})
                else:
                    for field, errors in all_errors.items():
                        for error in errors:
                            messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                    return redirect('/?edit=1')
                    
            # 4. If all validations pass: save draft application + documents to DB
            with transaction.atomic():
                app_id = request.session.get('draft_app_id')
                if app_id:
                    app = StudentApplication.objects.filter(id=app_id).first()
                else:
                    app = None
                if not app:
                    status_obj, _ = ApplicationStatus.objects.get_or_create(code='INCOMPLETE', defaults={'name': 'Incomplete'})
                    app = StudentApplication(status=status_obj)
                if not app.application_number:
                    app.application_number = f"DRAFT-{get_random_string(8)}"
                populate_app_from_data(app, form.cleaned_data)
                app.save()
                request.session['draft_app_id'] = app.id
                save_documents_to_db(app, temp_files)
            
            request.session['temp_application_data'] = form_data
            completed = list(request.session.get('completed_sections', []))
            for sec in ['personal-details', 'contact-details', 'education-details', 'document-uploads']:
                if sec not in completed:
                    completed.append(sec)
            request.session['completed_sections'] = completed
            request.session.modified = True
            
            from django.urls import reverse
            preview_url = reverse('registration_preview', args=[app.id])
            if is_ajax:
                return JsonResponse({"success": True, "redirect_url": preview_url})
            return redirect(preview_url)
            
        except Exception as e:
            # Generate a short error id to help support trace this failure without exposing internals
            error_id = get_random_string(10)
            logger.exception(f"Error during submit_application (id={error_id})")
            if is_ajax:
                return JsonResponse({
                    "success": False,
                    "errors": {"__all__": [f"Server processing error (reference: {error_id}). Please try again; if the problem continues contact support and provide the reference id."]}
                })
            messages.error(request, f'We encountered a server error while processing your files (reference: {error_id}). Please try again, and contact support if the problem continues.')
            return redirect('/?edit=1')
            
    if is_ajax:
        return JsonResponse({"success": False, "errors": {"__all__": ["Invalid request method."]}})
    messages.error(request, 'Invalid request method.')
    return redirect('registration')

def preview_application(request):
    """
    Legacy /preview/ URL. Redirects to the DB-backed preview page
    using the current draft application id.
    """
    app_id = request.session.get('draft_app_id')
    if app_id:
        return redirect('registration_preview', application_id=app_id)
    return redirect('registration')

def registration_preview(request, application_id):
    """
    Step 2: Render the Preview Page using the saved database record.
    The student's application is loaded by application_id and all data
    (personal, contact, education, identification, documents) is shown
    from the database, not from unsaved browser values.
    """
    app = get_object_or_404(StudentApplication, id=application_id)
    
    session_app_id = request.session.get('draft_app_id')
    if session_app_id:
        try:
            own_application = int(session_app_id) == application_id
        except (ValueError, TypeError):
            own_application = False
    else:
        own_application = False

    # Security: only allow viewing an application that belongs to this session.
    if not own_application:
        messages.error(request, 'Application not found.')
        return redirect('registration')
    if app.is_submitted:
        messages.error(request, 'This application has already been submitted.')
        return redirect('registration')
    
    files = request.session.get('temp_files', {})
    context = build_preview_context(app, files)
    return render(request, 'registration/preview.html', context)

def final_submit(request):
    """
    Step 3: Finalize submission of the DB-backed draft application.
    The draft (and its documents) were saved when the student clicked
    "Generate Preview". Here we assign the application number, mark the
    status as PENDING, generate acknowledgement files, clear the session
    and send the notification.
    """
    if request.method != 'POST':
        return redirect('registration')
    
    app_id = request.POST.get('application_id') or request.session.get('draft_app_id')
    if not app_id:
        messages.error(request, 'No application found to submit. Please start over.')
        return redirect('registration')
    
    app = StudentApplication.objects.filter(id=app_id).first()
    if not app:
        messages.error(request, 'Application not found. Please start over.')
        return redirect('registration')
    # Secondary Validation against bypassed requests.
    # Re-validate the latest form data (from the session if available,
    # otherwise the stored draft itself) using the full server-side rules.
    data = request.session.get('temp_application_data')
    if data:
        form = StudentApplicationForm(data=data, instance=app)
    else:
        form = StudentApplicationForm(data=app_to_form_data(app), instance=app)
    if not form.is_valid():
        messages.error(request, 'Validation failed. Please review your application.')
        return redirect('registration_preview', application_id=app.id)

    files = request.session.get('temp_files', {})
    
    try:
        with transaction.atomic():
            # Authoritative duplicate check: only SUBMITTED applications block.
            # A draft never blocks; the current application is always excluded.
            dupe_q = Q(pk__in=[])
            identity_values = {
                'mobile_number': form.cleaned_data.get('mobile_number'),
                'aadhaar_number': form.cleaned_data.get('aadhaar_number'),
                'email': form.cleaned_data.get('email'),
                'abc_id': form.cleaned_data.get('abc_id'),
                'registration_number': form.cleaned_data.get('registration_number'),
            }
            for fld, val in identity_values.items():
                if val:
                    dupe_q |= Q(**{fld: val})
            submitted_dupes = StudentApplication.objects.filter(
                dupe_q, status__code__in=SUBMITTED_STATUS_CODES
            ).exclude(pk=app.pk)
            if submitted_dupes.exists():
                messages.error(request, 'An application with the same Mobile number, Aadhaar number, or Email already exists and has been submitted.')
                return redirect('registration_preview', application_id=app.id)

            # Verify all mandatory documents exist for this application
            existing_docs = {d.lower() for d in UploadedDocument.objects.filter(application=app).values_list('doc_type', flat=True)}
            # Additional documents are optional; require core mandatory documents only
            mandatory_doc_types = ['passport_photo', 'signature', 'aadhaar', 'left_thumb', 'father_signature', 'community_certificate']
            missing_docs = [d for d in mandatory_doc_types if d not in existing_docs]
            if missing_docs:
                # Provide a clear, user-friendly list of missing document names
                pretty = ', '.join([d.replace('_', ' ').title() for d in missing_docs])
                messages.error(request, f'Missing mandatory documents: {pretty}. Please upload them before final submission.')
                # Instead of redirecting (which can lose transient messages in some test setups),
                # render the preview page directly so the message appears in the response body.
                context = build_preview_context(app, files)
                return render(request, 'registration/preview.html', context)

            app_no = generate_application_number()
            aadhaar_num = app.aadhaar_number or ''
            full_nm = app.full_name or ''

            storage_folder_name = get_student_folder_name(aadhaar_num, full_nm)
            
            # Persist the re-validated data so the submitted record always
            # reflects the server-validated values.
            populate_app_from_data(app, form.cleaned_data)
            app.application_number = app_no
            app.storage_folder = storage_folder_name
            status, _ = ApplicationStatus.objects.get_or_create(code='SUBMITTED', defaults={'name': 'Submitted'})
            app.status = status
            app.ip_address = request.META.get('REMOTE_ADDR')
            app.save()
            
            # Ensure any session-only files are persisted (idempotent)
            if files and not UploadedDocument.objects.filter(application=app).exists():
                save_documents_to_db(app, files)
            
            # Clean up session and temp dir
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', request.session.session_key or 'anon')
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                
            if 'temp_application_data' in request.session:
                del request.session['temp_application_data']
            if 'temp_files' in request.session:
                del request.session['temp_files']
            if 'draft_app_id' in request.session:
                del request.session['draft_app_id']
            if 'completed_sections' in request.session:
                del request.session['completed_sections']
                
            # Generate Acknowledgement files
            generate_acknowledgement_files(app)
            
            # Send Email Notification
            from django.core.mail import send_mail
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
        # Log full traceback and provide a short opaque reference to the user
        error_id = get_random_string(10)
        logger.exception(f"Error during final_submit (ref={error_id})")
        user_msg = f'We encountered an error while saving your application (reference: {error_id}). Please try again, and contact support if the problem continues.'
        messages.error(request, user_msg)
        # If app exists, redirect back to preview for the same application; otherwise send user to registration
        try:
            return redirect('registration_preview', application_id=app.id)
        except Exception:
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
        exists = StudentApplication.objects.filter(
            **{field: value}, status__code__in=SUBMITTED_STATUS_CODES
        ).exists()
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
                if not value or not re.match(r"^[1-9]\d{9}$", value):
                    return JsonResponse({'success': False, 'message': 'Number must be 10 digits and cannot start with 0.'})
            elif field == 'alternative_mobile':
                if value and not re.match(r"^[1-9]\d{9}$", value):
                    return JsonResponse({'success': False, 'message': 'Number must be 10 digits and cannot start with 0.'})
            elif field == 'aadhaar_number':
                if not value or not re.match(r"^[1-9]\d{11}$", value):
                    return JsonResponse({'success': False, 'message': 'Aadhaar number must be 12 digits and cannot start with 0.'})
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
                app = StudentApplication(status=status_obj)
                app.application_number = f"DRAFT-{get_random_string(8)}"
                app.save()
                request.session['draft_app_id'] = app.id
                request.session.modified = True
                
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
                
            return JsonResponse({'success': True, 'message': '\u2713 Already saved'})
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
    # Pincode lookup API has been disabled to make Pincode independent from State/District.
    # This endpoint intentionally returns a neutral response and performs no DB or session changes.
    return JsonResponse({'success': False, 'message': 'Pincode lookup disabled.'})

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


def find_registration(request):
    """
    Search By Aadhaar Number or Email Address to:
    - Case 1: Detect already submitted applications and display safe status info.
    - Case 2: Restore existing draft applications into the session so user can continue.
    - Case 3: Detect new users with no records and carry forward the identifier to the form.
    """
    import re
    search_by = request.GET.get('search_by') or request.POST.get('search_by', '')
    search_value = request.GET.get('search_value') or request.POST.get('search_value', '')

    search_by = str(search_by).strip().lower()
    search_value = str(search_value).strip()

    if not search_by or not search_value:
        return JsonResponse({
            'success': False,
            'error': 'Please provide both Search By criteria and a value.'
        }, status=400)

    if search_by not in ['aadhaar', 'email']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid search criteria. Please select Aadhaar Number or Email Address.'
        }, status=400)

    if search_by == 'aadhaar':
        clean_val = re.sub(r'[\s\-]', '', search_value)
        if not re.match(r'^\d{12}$', clean_val):
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid 12-digit Aadhaar Number.'
            }, status=400)
        filter_kwargs = {'aadhaar_number': clean_val}
        masked_val = f"********{clean_val[-4:]}"
        field_name = "Aadhaar Number"
    else:
        clean_val = search_value.lower()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', clean_val):
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid Email Address.'
            }, status=400)
        filter_kwargs = {'email__iexact': clean_val}
        parts = clean_val.split('@')
        user_part = parts[0]
        domain_part = parts[1] if len(parts) > 1 else ''
        if len(user_part) <= 2:
            masked_user = user_part[0] + '*'
        else:
            masked_user = user_part[0] + ('*' * (len(user_part) - 2)) + user_part[-1]
        masked_val = f"{masked_user}@{domain_part}"
        field_name = "Email Address"

    # 1. CASE 1: Check for submitted application
    submitted_app = StudentApplication.objects.filter(
        **filter_kwargs,
        status__code__in=SUBMITTED_STATUS_CODES
    ).order_by('-submission_date', '-id').first()

    if submitted_app:
        sub_date_str = submitted_app.submission_date.strftime('%d-%b-%Y') if submitted_app.submission_date else ''
        status_name = submitted_app.status.name if submitted_app.status else 'Submitted'
        
        # Always format the actual stored Aadhaar number with mask
        raw_aadhaar = str(submitted_app.aadhaar_number or '')
        aadhaar_digits = re.sub(r'[^0-9]', '', raw_aadhaar)
        masked_aadhaar = f"********{aadhaar_digits[-4:]}" if len(aadhaar_digits) >= 4 else "********"

        return JsonResponse({
            'success': True,
            'case': 'submitted',
            'status': 'submitted',
            'title': 'Your application has already been submitted.',
            'message': 'An application has already been submitted and registered in the system. Duplicate applications cannot be created.',
            'details': {
                'status': status_name,
                'submission_date': sub_date_str,
                'masked_aadhaar': masked_aadhaar,
            }
        })

    # 2. CASE 2: Check for existing draft application
    draft_app = StudentApplication.objects.filter(
        **filter_kwargs
    ).exclude(
        status__code__in=SUBMITTED_STATUS_CODES
    ).order_by('-last_updated', '-id').first()

    if draft_app:
        # Load draft data into session
        request.session['draft_app_id'] = draft_app.id
        draft_form_data = app_to_form_data(draft_app)
        request.session['temp_application_data'] = draft_form_data

        # Determine completed sections
        completed = []
        if draft_form_data.get('full_name') and draft_form_data.get('dob') and draft_form_data.get('gender') and draft_form_data.get('father_name') and draft_form_data.get('mother_name'):
            completed.append('personal-details')
        if 'personal-details' in completed and draft_form_data.get('mobile_number') and draft_form_data.get('aadhaar_number') and draft_form_data.get('email') and draft_form_data.get('communication_address') and draft_form_data.get('state') and draft_form_data.get('district'):
            completed.append('contact-details')
        if 'contact-details' in completed and draft_form_data.get('qualification') and draft_form_data.get('applying_qualification') and draft_form_data.get('institution') and draft_form_data.get('hall_ticket_number') and draft_form_data.get('mode_of_qualification') and draft_form_data.get('completion_status') and draft_form_data.get('year_of_passing') and draft_form_data.get('program_opting'):
            completed.append('education-details')

        request.session['completed_sections'] = completed
        request.session.modified = True

        last_updated_str = draft_app.last_updated.strftime('%d-%b-%Y %I:%M %p') if draft_app.last_updated else ''

        return JsonResponse({
            'success': True,
            'case': 'draft',
            'status': 'draft',
            'title': 'Your saved registration details have been found.',
            'message': 'You can continue your registration from where you left off. All your previously saved details and documents have been restored.',
            'app_id': draft_app.id,
            'last_updated': last_updated_str,
            'redirect_url': f"/?app_id={draft_app.id}&resumed=1",
            'form_data': draft_form_data,
            'completed_sections': completed,
            'details': {
                'identifier_masked': masked_val,
                'search_by': search_by,
                'search_by_label': field_name,
                'completed_count': len(completed)
            }
        })

    # 3. CASE 3: No Record Found (New User)
    return JsonResponse({
        'success': True,
        'case': 'not_found',
        'status': 'not_found',
        'title': 'No registration found.',
        'message': f'No registration was found with the provided {field_name}. You can start a new registration.',
        'search_by': search_by,
        'search_by_label': field_name,
        'search_value': clean_val
    })
