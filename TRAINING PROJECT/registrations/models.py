from django.db import models
from django.contrib.auth.models import User
from masterdata.models import (
    Country, State, District, Religion, Qualification, Program, 
    Occupation, Community, MaritalStatus, ApplicationStatus,
    YearOfStudy, ExServiceStatus, VerificationStatus, TrainingPartner
)
from utilities.folder_manager import get_upload_path, get_acknowledgement_path
from .validators import (
    validate_person_name,
    validate_indian_mobile,
    validate_indian_pincode,
    validate_hall_ticket,
    validate_aadhaar
)

class StudentApplication(models.Model):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]

    application_number = models.CharField(max_length=50, unique=True, blank=True)
    storage_folder = models.CharField(max_length=255, blank=True, null=True, help_text="Stable media folder name based on Aadhaar and Name")
    
    CATEGORY_CHOICES = [
        ('OC (General)', 'OC (General)'),
        ('EWS', 'EWS'),
        ('BC-A', 'BC-A'),
        ('BC-B', 'BC-B'),
        ('BC-C', 'BC-C'),
        ('BC-D', 'BC-D'),
        ('BC-E', 'BC-E'),
        ('SC', 'SC'),
        ('ST', 'ST'),
    ]
    NATIONALITY_CHOICES = [
        ('Indian', 'Indian'),
        ('Other', 'Other'),
    ]
    YES_NO_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]
    
    APPLYING_QUALIFICATION_CHOICES = [
        ('10th Pass (SSC)', '10th Pass (SSC)'),
        ('Intermediate (10+2)', 'Intermediate (10+2)'),
        ('ITI', 'ITI'),
        ('Polytechnic Diploma', 'Polytechnic Diploma'),
        ('Diploma in Engineering', 'Diploma in Engineering'),
        ('Pursuing Diploma', 'Pursuing Diploma'),
        ('Completed Diploma', 'Completed Diploma'),
        ('Pursuing 1st Year of UG', 'Pursuing 1st Year of UG'),
        ('Pursuing 2nd Year of UG', 'Pursuing 2nd Year of UG'),
        ('Pursuing 3rd Year of UG', 'Pursuing 3rd Year of UG'),
        ('Pursuing 4th Year of UG', 'Pursuing 4th Year of UG'),
        ('BA', 'BA'),
        ('B.Com', 'B.Com'),
        ('B.Sc', 'B.Sc'),
        ('BCA', 'BCA'),
        ('BBA', 'BBA'),
        ('B.Tech / BE', 'B.Tech / BE'),
        ('MBBS', 'MBBS'),
        ('BDS', 'BDS'),
        ('B.Pharmacy', 'B.Pharmacy'),
        ('B.Ed', 'B.Ed'),
        ('LLB', 'LLB'),
        ('MCA', 'MCA'),
        ('MBA', 'MBA'),
        ('M.Tech / ME', 'M.Tech / ME'),
        ('M.Sc', 'M.Sc'),
        ('M.Com', 'M.Com'),
        ('MA', 'MA'),
        ('Ph.D', 'Ph.D'),
        ('Other', 'Other')
    ]

    MODE_OF_QUALIFICATION_CHOICES = [
        ('Full Time', 'Full Time'),
        ('Part Time', 'Part Time'),
        ('Distance', 'Distance'),
        ('Online', 'Online')
    ]

    COMPLETION_STATUS_CHOICES = [
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed')
    ]

    # Personal
    full_name = models.CharField(max_length=150, null=True, blank=True, validators=[validate_person_name])
    father_name = models.CharField(max_length=150, null=True, blank=True, validators=[validate_person_name])
    mother_name = models.CharField(max_length=150, null=True, blank=True, validators=[validate_person_name])
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    religion = models.ForeignKey(Religion, on_delete=models.RESTRICT, null=True, blank=True)
    marital_status = models.ForeignKey(MaritalStatus, on_delete=models.RESTRICT, null=True, blank=True)
    community = models.ForeignKey(Community, on_delete=models.RESTRICT, null=True, blank=True)
    ex_serviceman = models.ForeignKey(ExServiceStatus, on_delete=models.RESTRICT, null=True, blank=True)
    occupation = models.ForeignKey(Occupation, on_delete=models.RESTRICT, null=True, blank=True)
    
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OC (General)', null=True, blank=True)
    nationality = models.CharField(max_length=50, choices=NATIONALITY_CHOICES, default='Indian', null=True, blank=True)
    physically_handicapped = models.CharField(max_length=10, choices=YES_NO_CHOICES, default='No', null=True, blank=True)
    annual_income = models.PositiveIntegerField(default=0, null=True, blank=True)

    # Contact
    mobile_number = models.CharField(max_length=10, unique=True, null=True, blank=True, validators=[validate_indian_mobile])
    alternative_mobile = models.CharField(max_length=10, blank=True, null=True, validators=[validate_indian_mobile])
    email = models.EmailField(unique=True, null=True, blank=True)
    communication_address = models.TextField()
    country = models.ForeignKey(Country, on_delete=models.RESTRICT, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.RESTRICT, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.RESTRICT, null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True, validators=[validate_indian_pincode])

    # Educational
    applying_qualification = models.CharField(max_length=50, choices=APPLYING_QUALIFICATION_CHOICES, default='10th Pass (SSC)')
    qualification = models.ForeignKey(Qualification, on_delete=models.RESTRICT, null=True, blank=True)
    custom_stream = models.CharField(max_length=100, blank=True, null=True)
    mode_of_qualification = models.CharField(max_length=20, choices=MODE_OF_QUALIFICATION_CHOICES, default='Full Time')
    completion_status = models.CharField(max_length=20, choices=COMPLETION_STATUS_CHOICES, default='Completed')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    year_of_passing = models.IntegerField(default=2024, null=True, blank=True)
    training_partner = models.ForeignKey(TrainingPartner, on_delete=models.RESTRICT, null=True, blank=True)
    batch_code = models.CharField(max_length=50, blank=True, null=True)
    program_opting = models.ForeignKey(Program, on_delete=models.RESTRICT, null=True, blank=True)
    
    # Old fields removed or replaced: year_of_study
    institution = models.CharField(max_length=200, null=True, blank=True)
    hall_ticket_number = models.CharField(max_length=50, null=True, blank=True, validators=[validate_hall_ticket])
    registration_number = models.CharField(max_length=50, unique=True, null=True, blank=True)

    # Identification
    aadhaar_number = models.CharField(max_length=12, unique=True, null=True, blank=True, validators=[validate_aadhaar])
    abc_id = models.CharField(max_length=12, unique=True, null=True, blank=True)
    distinguishing_mark = models.CharField(max_length=255, null=True, blank=True)

    # Status
    status = models.ForeignKey(ApplicationStatus, on_delete=models.SET_NULL, null=True)
    verification_status = models.ForeignKey(VerificationStatus, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approval_date = models.DateTimeField(blank=True, null=True)
    
    # Tracking
    submission_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    browser_info = models.TextField(blank=True, null=True)
    
    # Consent
    consent_given = models.BooleanField(default=False)

    # Acknowledgement Files
    acknowledgement_pdf = models.FileField(upload_to=get_acknowledgement_path, blank=True, null=True)
    acknowledgement_png = models.FileField(upload_to=get_acknowledgement_path, blank=True, null=True)
    acknowledgement_jpg = models.FileField(upload_to=get_acknowledgement_path, blank=True, null=True)

    def __str__(self):
        return f"{self.application_number} - {self.full_name}"

class UploadedDocument(models.Model):
    application = models.ForeignKey(StudentApplication, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=50)
    original_file = models.FileField(upload_to=get_upload_path)
    compressed_file = models.FileField(upload_to=get_upload_path, blank=True, null=True)
    
    # Audit Metadata
    original_file_size = models.PositiveIntegerField(blank=True, null=True, help_text="Size in bytes")
    optimized_file_size = models.PositiveIntegerField(blank=True, null=True, help_text="Size in bytes")
    image_width = models.PositiveIntegerField(blank=True, null=True)
    image_height = models.PositiveIntegerField(blank=True, null=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    compression_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    jpeg_quality = models.PositiveIntegerField(blank=True, null=True)
    validation_status = models.CharField(max_length=20, blank=True, null=True)
    processing_policy = models.CharField(max_length=50, blank=True, null=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.application_number} - {self.doc_type}"

    @property
    def original_size_kb(self):
        if self.original_file_size:
            return round(self.original_file_size / 1024.0, 2)
        return None

    @property
    def optimized_size_kb(self):
        if self.optimized_file_size:
            return round(self.optimized_file_size / 1024.0, 2)
        return None

    @property
    def actual_dpi(self):
        if not self.mime_type or not self.mime_type.startswith('image/'):
            return None
        file_field = self.compressed_file if self.compressed_file else self.original_file
        if not file_field:
            return None
        try:
            from PIL import Image
            with Image.open(file_field.path) as img:
                dpi = img.info.get('dpi')
                if dpi:
                    return f'{int(dpi[0])} x {int(dpi[1])}'
        except Exception:
            pass
        return None

    @property
    def original_filename(self):
        if not self.original_file:
            return ""
        from pathlib import Path
        return Path(self.original_file.name).name

    @property
    def compressed_filename(self):
        if not self.compressed_file:
            return ""
        from pathlib import Path
        return Path(self.compressed_file.name).name

    @property
    def compressed_size_kb(self):
        if not self.compressed_file:
            return None
        try:
            return round(self.compressed_file.size / 1024.0, 2)
        except (FileNotFoundError, OSError):
            return None

    @property
    def doc_type_display(self):
        return self.doc_type.replace('_', ' ').title()

