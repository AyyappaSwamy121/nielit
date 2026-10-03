"""Seed the Form Builder database configuration from the current application form.

Usage:
    python manage.py seed_form_builder [--force]

Idempotent: existing sections/fields are matched by slug/field_name and updated
in place, so re-running is safe. Never deletes application data.
"""

from django.core.management.base import BaseCommand

from dashboard.models import FormSection, FormFieldConfiguration, FormFieldOption


# ---------------------------------------------------------------------------
# Section definitions (order matters - it drives rendering order)
# ---------------------------------------------------------------------------
SECTIONS = [
    {'slug': 'personal-details', 'name': 'Personal Details', 'icon': 'person', 'order': 1,
     'description': 'Candidate personal and identification details.'},
    {'slug': 'contact-details', 'name': 'Contact Details', 'icon': 'contact_mail', 'order': 2,
     'description': 'Mobile, email and communication address.'},
    {'slug': 'education-details', 'name': 'Educational Details', 'icon': 'school', 'order': 3,
     'description': 'Qualification, stream, percentage and year of passing.'},
    {'slug': 'document-uploads', 'name': 'Document Uploads', 'icon': 'upload_file', 'order': 4,
     'description': 'Photograph, signature, thumb impression and certificates.'},
    {'slug': 'declaration', 'name': 'Declaration', 'icon': 'check_circle', 'order': 5,
     'description': 'Consent and declaration.'},
    {'slug': 'additional-documents', 'name': 'Additional Documents', 'icon': 'attach_file', 'order': 6,
     'description': 'Additional supporting documents.'},
]


def _opt(value):
    return [{'value': v, 'label': v} for v in value]


# ---------------------------------------------------------------------------
# Field definitions
# ---------------------------------------------------------------------------
FIELDS = [
    # ---------------- Personal Details ----------------
    dict(field_name='full_name', section='personal-details', label='Name (as per Aadhaar)',
         field_type='text', required=True, placeholder='Enter name as per Aadhaar',
         max_length=150, validator_type='alphabetic', order=1),
    dict(field_name='dob', section='personal-details', label='Date of Birth',
         field_type='date', required=True, order=2),
    dict(field_name='gender', section='personal-details', label='Gender',
         field_type='select', required=True, options=_opt(['Male', 'Female']), order=3),
    dict(field_name='father_name', section='personal-details', label="Father's Name",
         field_type='text', required=True, placeholder="Enter your father's name",
         max_length=150, validator_type='alphabetic', order=4),
    dict(field_name='mother_name', section='personal-details', label="Mother's Name",
         field_type='text', required=True, placeholder="Enter your mother's name",
         max_length=150, validator_type='alphabetic', order=5),
    dict(field_name='marital_status', section='personal-details', label='Marital Status',
         field_type='select', required=True, options_source='masterdata',
         source_model='MaritalStatus', order=6),
    dict(field_name='ex_serviceman', section='personal-details', label='Ex-Service Man',
         field_type='select', required=True, options_source='masterdata',
         source_model='ExServiceStatus', order=7),
    dict(field_name='religion', section='personal-details', label='Religion',
         field_type='select', required=True, options_source='masterdata',
         source_model='Religion', order=8),
    dict(field_name='community', section='personal-details', label='Category',
         field_type='select', required=True, options_source='masterdata',
         source_model='Community', order=9),
    dict(field_name='nationality', section='personal-details', label='Nationality',
         field_type='select', required=True, options=_opt(['Indian', 'Other']), order=10),
    dict(field_name='physically_handicapped', section='personal-details', label='Physically Handicapped',
         field_type='select', required=True, options=_opt(['Yes', 'No']), order=11),
    dict(field_name='annual_income', section='personal-details', label='Annual Income',
         field_type='number', required=True, placeholder='Enter annual income',
         min_value=0, order=12),

    # ---------------- Contact Details ----------------
    dict(field_name='mobile_number', section='contact-details', label='Mobile Number',
         field_type='phone', required=True, placeholder='Enter 10-digit mobile number',
         min_length=10, max_length=10, validator_type='phone', order=1),
    dict(field_name='aadhaar_number', section='contact-details', label='Aadhaar Number',
         field_type='aadhaar', required=True, placeholder='Enter 12-digit Aadhaar',
         min_length=12, max_length=12, validator_type='aadhaar', order=2),
    dict(field_name='alternative_mobile', section='contact-details', label='Alternate Phone Number',
         field_type='phone', required=False, placeholder='Enter alternative mobile',
         min_length=10, max_length=10, validator_type='phone', order=3),
    dict(field_name='email', section='contact-details', label='Email Address',
         field_type='email', required=True, placeholder='Enter your email address',
         validator_type='email', order=4),
    dict(field_name='communication_address', section='contact-details', label='Complete Address',
         field_type='textarea', required=True, placeholder='Enter your full address',
         min_length=10, order=5),
    dict(field_name='state', section='contact-details', label='State',
         field_type='select', required=True, options_source='masterdata',
         source_model='State', order=6),
    dict(field_name='district', section='contact-details', label='District',
         field_type='select', required=True, options_source='masterdata',
         source_model='District', order=7),
    dict(field_name='pincode', section='contact-details', label='Pincode',
         field_type='pincode', required=True, placeholder='Enter 6-digit pincode',
         min_length=6, max_length=6, validator_type='pincode', order=8),
    dict(field_name='occupation', section='contact-details', label='Occupation',
         field_type='select', required=True, options_source='masterdata',
         source_model='Occupation', order=9),
    dict(field_name='country', section='contact-details', label='Country',
         field_type='text', required=True, placeholder='India', order=10),

    # ---------------- Educational Details ----------------
    dict(field_name='applying_qualification', section='education-details', label='Applying Qualification',
         field_type='select', required=True, options=_opt([
             '12th or equivalent',
             '2yrs of 3 yr dip in ECE/EE/CS/IT and allied branches after 10th',
             'Previous relevant Qualification of NSQF Level 3',
             'Previous relevant Qualification of NSQF Level 5',
             'Pursing 3rd yr of UG in CS/IT /ECE/EE/allied branches',
             'Completed 3 year of UG in CS/IT/ECE/EE/allied branches',
         ]), order=1),
    dict(field_name='mode_of_qualification', section='education-details', label='Mode of Qualification',
         field_type='select', required=True, options=_opt(['Full Time', 'Part Time', 'Distance', 'Online']), order=2),
    dict(field_name='completion_status', section='education-details', label='Completion Status',
         field_type='select', required=True, options=_opt(['Ongoing', 'Completed']), order=3),
    dict(field_name='qualification', section='education-details', label='Stream of Qualification',
         field_type='select', required=True, options_source='masterdata',
         source_model='Qualification', order=4),
    dict(field_name='custom_stream', section='education-details', label='Specify Stream of Qualification',
         field_type='text', required=False, placeholder='Specify Stream of Qualification',
         is_conditional=True, order=5),
    dict(field_name='percentage', section='education-details', label='Percentage (%)',
         field_type='number', required=False, placeholder='Enter Percentage',
         validator_type='percentage', min_value=0, max_value=100, order=6),
    dict(field_name='year_of_passing', section='education-details', label='Year of Passing',
         field_type='select', required=True, min_value=1950, order=7),
    dict(field_name='training_partner', section='education-details', label='Training Partner/ATC',
         field_type='select', required=True, options_source='masterdata',
         source_model='TrainingPartner', order=8),
    dict(field_name='batch_code', section='education-details', label='Batch Code',
         field_type='text', required=True, readonly=True, order=9),
    dict(field_name='program_opting', section='education-details', label='Name of the program opting',
         field_type='select', required=True, options_source='masterdata',
         source_model='Program', order=10),
    dict(field_name='institution', section='education-details', label='Name of Educational Institution',
         field_type='text', required=True, order=11),
    dict(field_name='hall_ticket_number', section='education-details', label='Hall Ticket Number',
         field_type='text', required=True, max_length=50, order=12),
    dict(field_name='registration_number', section='education-details', label='Registration Number',
         field_type='text', required=True, max_length=50, order=13),
    dict(field_name='abc_id', section='education-details', label='ABC ID (Apaar ID)',
         field_type='text', required=True, min_length=12, max_length=12,
         regex_pattern=r'^[0-9]{12}$', order=14),

    # ---------------- Document Uploads ----------------
    dict(field_name='upload_passport_photo', section='document-uploads', label='Passport Size Photograph',
         field_type='file', required=True, allowed_file_types=['jpg', 'jpeg', 'png'],
         max_file_size=2048, help_text='Passport size photo in JPG/JPEG/PNG format', order=1),
    dict(field_name='upload_signature', section='document-uploads', label='Signature',
         field_type='file', required=True, allowed_file_types=['jpg', 'jpeg', 'png'],
         max_file_size=2048, help_text='Scanned signature on white paper with black/blue ink as Image File', order=2),
    dict(field_name='upload_aadhaar', section='document-uploads', label='Aadhaar Card',
         field_type='file', required=True, allowed_file_types=['pdf'],
         max_file_size=2048, help_text='Scanned copy of valid Aadhaar card as PDF', order=3),
    dict(field_name='upload_left_thumb', section='document-uploads', label='Thumb Impression',
         field_type='file', required=True, allowed_file_types=['jpg', 'jpeg', 'png'],
         max_file_size=2048, help_text='Left thumb impression in JPG/JPEG/PNG format', order=4),
    dict(field_name='upload_abc_id', section='document-uploads', label='ABC ID (Apaar ID)',
         field_type='file', required=True, allowed_file_types=['pdf', 'jpg', 'jpeg', 'png'],
         max_file_size=2048, help_text='ABC ID in PDF or image format', order=5),
    dict(field_name='upload_father_signature', section='document-uploads', label="Father's/Guardian's Signature",
         field_type='file', required=True, allowed_file_types=['jpg', 'jpeg', 'png'],
         max_file_size=2048, help_text="Father's/Guardian's signature as Image File", order=6),
    dict(field_name='upload_community_certificate', section='document-uploads', label='Community Certificate',
         field_type='file', required=False, allowed_file_types=['pdf'],
         max_file_size=2048, help_text='Community certificate as PDF', order=7),
    dict(field_name='distinguishing_mark', section='document-uploads', label='Distinguishing Mark',
         field_type='text', required=True, min_length=5, max_length=100,
         validator_type='alphabetic', order=8),

    # ---------------- Declaration ----------------
    dict(field_name='consent_given', section='declaration', label='Aadhaar Consent / Declaration',
         field_type='checkbox', required=True, order=1),

    # ---------------- Additional Documents ----------------
    dict(field_name='upload_additional_documents', section='additional-documents',
         label='Additional Documents (Single PDF)', field_type='file', required=True,
         allowed_file_types=['pdf'], max_file_size=2048,
         help_text='Upload a document supporting the applying qualification. PDF only.', order=1),
]


class Command(BaseCommand):
    help = 'Seed the Form Builder configuration from the current application form.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Re-seed even if configuration already exists.')

    def handle(self, *args, **options):
        from dashboard.models import FormFieldConfiguration
        force = options['force']
        existing = FormFieldConfiguration.objects.exists()
        if existing and not force:
            self.stdout.write(self.style.WARNING(
                'Form configuration already exists. Use --force to re-seed.'
            ))
            return

        sections = {}
        for s in SECTIONS:
            obj, _ = FormSection.objects.update_or_create(
                slug=s['slug'],
                defaults={
                    'name': s['name'],
                    'icon': s['icon'],
                    'description': s['description'],
                    'display_order': s['order'],
                    'is_active': True,
                },
            )
            sections[s['slug']] = obj
            self.stdout.write(self.style.SUCCESS(f'Section: {obj.name}'))

        for f in FIELDS:
            section = sections[f['section']]
            opts = f.pop('options', [])
            defaults = dict(f)
            defaults.pop('section', None)
            if 'order' in defaults:
                defaults['display_order'] = defaults.pop('order')
            defaults['section'] = section
            obj, created = FormFieldConfiguration.objects.update_or_create(
                field_name=f['field_name'],
                defaults=defaults,
            )
            # Seed admin-managed options only for static-option fields.
            if opts:
                existing_ids = set(FormFieldOption.objects.filter(field=obj).values_list('id', flat=True))
                FormFieldOption.objects.filter(field=obj).delete()
                for i, opt in enumerate(opts):
                    FormFieldOption.objects.create(
                        field=obj, label=opt['label'], value=opt['value'], display_order=i,
                    )
            self.stdout.write(self.style.SUCCESS(
                f"Field: {obj.label} [{'created' if created else 'updated'}]"
            ))

        total = FormFieldConfiguration.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Form Builder seeded successfully. Total fields: {total}'
        ))