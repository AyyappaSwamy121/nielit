from django import forms
from django.core.exceptions import ValidationError
from .models import StudentApplication, SUBMITTED_STATUS_CODES
from masterdata.models import District, State, Country
class StudentApplicationForm(forms.ModelForm):

    institution = forms.ChoiceField(
        required=True,
        choices=(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "institution",
                "autocomplete": "off",
            }
        ),
    )

    percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        error_messages={
            "invalid": "Enter a valid percentage between 0 and 100.",
            "max_digits": "Enter a valid percentage between 0 and 100.",
            "max_decimal_places": "Enter a valid percentage between 0 and 100.",
            "max_whole_digits": "Enter a valid percentage between 0 and 100.",
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from masterdata.models import EducationalInstitution
        try:
            institutions = EducationalInstitution.objects.filter(is_active=True).order_by('name')
            inst_choices = [(inst.name, inst.name) for inst in institutions]
        except Exception:
            inst_choices = []

        current_val = None
        if self.is_bound:
            current_val = self.data.get('institution')
            if current_val == 'Other' and self.data.get('other_institution'):
                current_val = self.data.get('other_institution').strip()
        elif self.instance and self.instance.pk and self.instance.institution:
            current_val = self.instance.institution
        elif self.initial.get('institution'):
            current_val = self.initial.get('institution')

        if current_val and current_val not in [c[0] for c in inst_choices] and current_val != 'Other':
            inst_choices.append((current_val, current_val))

        self.fields['institution'].choices = [
            ("", "Select Educational Institution"),
            *inst_choices,
            ("Other", "Other"),
        ]

        required_fields = [
            'full_name', 'father_name', 'mother_name', 'dob', 'gender',
            'nationality', 'mobile_number', 'email', 'communication_address',
            'country', 'state', 'district', 'institution',
            'hall_ticket_number', 'applying_qualification', 'qualification',
            'program_opting', 'mode_of_qualification', 'completion_status',
            'year_of_passing', 'aadhaar_number', 'distinguishing_mark'
        ]

        for field in required_fields:
            if field in self.fields:
                self.fields[field].required = True
                self.fields[field].widget.attrs['required'] = 'required'

    class Meta:
        model = StudentApplication
        fields = [
            'full_name', 'father_name', 'mother_name', 'dob', 'gender',
            'religion', 'marital_status', 'community', 'ex_serviceman',
            'occupation', 'nationality', 'physically_handicapped',
            'annual_income', 'mobile_number', 'alternative_mobile', 'email',
            'communication_address', 'country', 'state', 'district', 'pincode', 'area_village_name',
            'institution', 'hall_ticket_number', 'registration_number',
            'nielit_registration_number',
            'applying_qualification', 'qualification', 'custom_stream',
            'program_opting',
            'mode_of_qualification', 'completion_status', 'percentage',
            'year_of_passing', 'training_partner', 'batch_code',
            'aadhaar_number', 'abc_id', 'distinguishing_mark', 'consent_given'
        ]
        error_messages = {
            'nielit_registration_number': {
                'max_length': 'NIELIT Registration Number cannot exceed 50 characters.'
            }
        }

    def clean_consent_given(self):
        consent = self.cleaned_data.get('consent_given')
        if not consent:
            raise forms.ValidationError("You must agree to the terms and conditions.")
        return consent

    def clean(self):
        cleaned_data = super().clean()
        mobile = cleaned_data.get('mobile_number')
        alt_mobile = cleaned_data.get('alternative_mobile')
        state = cleaned_data.get('state')
        district = cleaned_data.get('district')
        country = cleaned_data.get('country')
        gender = cleaned_data.get('gender')
        qualification = cleaned_data.get('qualification')
        program_opting = cleaned_data.get('program_opting')
        aadhaar = cleaned_data.get('aadhaar_number')
        email = cleaned_data.get('email')
        abc_id = cleaned_data.get('abc_id')
        reg_number = cleaned_data.get('registration_number')

        # Status-aware duplicate validation.
        # Only officially SUBMITTED applications block a new application.
        # Draft/Preview (INCOMPLETE) records never do. The current record
        # (when editing an existing application) is always excluded.
        def submitted_duplicate_exists(field, value):
            if not value:
                return False
            qs = StudentApplication.objects.filter(
                **{field: value}, status__code__in=SUBMITTED_STATUS_CODES
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            return qs.exists()

        if mobile and submitted_duplicate_exists('mobile_number', mobile):
            self.add_error('mobile_number', 'Student application with this Mobile number already exists.')
        if aadhaar and submitted_duplicate_exists('aadhaar_number', aadhaar):
            self.add_error('aadhaar_number', 'Student application with this Aadhaar number already exists.')
        if email and submitted_duplicate_exists('email', email):
            self.add_error('email', 'Student application with this Email already exists.')
        if abc_id and submitted_duplicate_exists('abc_id', abc_id):
            self.add_error('abc_id', 'Student application with this ABC ID already exists.')
        if reg_number and submitted_duplicate_exists('registration_number', reg_number):
            self.add_error('registration_number', 'Student application with this Registration number already exists.')

        # Validate required dropdown fields
        if not gender:
            self.add_error('gender', 'Gender is required.')
        if not state:
            self.add_error('state', 'State is required.')
        if not district:
            self.add_error('district', 'District is required.')
        if not country:
            self.add_error('country', 'Country is required.')
        if not qualification:
            self.add_error('qualification', 'Qualification is required.')
        if not program_opting:
            self.add_error('program_opting', 'Program opting is required.')

        # Alternative mobile != Primary mobile
        if mobile and alt_mobile and mobile == alt_mobile:
            self.add_error('alternative_mobile', 'Alternative mobile number cannot be the same as the primary mobile number.')

        # State belongs to Country
        if state and country:
            if not State.objects.filter(id=state.id, country=country).exists():
                self.add_error('state', 'Selected State does not belong to the selected Country.')

        # District belongs to State
        if district and state:
            if not District.objects.filter(id=district.id, state=state).exists():
                self.add_error('district', 'Selected District does not belong to the selected State.')
                
        # Force India
        india = Country.objects.filter(name__iexact='india').first()
        if india and country and country.id != india.id:
            self.add_error('country', 'Country must be India.')

        if 'mode_of_qualification' not in cleaned_data or not cleaned_data['mode_of_qualification']:
            self.add_error('mode_of_qualification', 'This field is required.')
        if 'completion_status' not in cleaned_data or not cleaned_data['completion_status']:
            self.add_error('completion_status', 'This field is required.')
        pct = cleaned_data.get('percentage')
        
        import datetime
        current_year = datetime.datetime.now().year
        
        status = cleaned_data.get('completion_status')
        yop = cleaned_data.get('year_of_passing')
        
        if status == 'Completed':
            if yop and yop > current_year:
                self.add_error('year_of_passing', 'Year cannot be greater than current year.')
            if pct is None:
                self.add_error('percentage', 'Percentage is mandatory for Completed status.')
        elif status == 'Ongoing':
            if yop and yop < current_year:
                self.add_error('year_of_passing', 'Year cannot be less than current year.')

        return cleaned_data

    def clean_percentage(self):
        pct = self.cleaned_data.get('percentage')
        if pct is not None:
            if pct < 0 or pct > 100:
                raise forms.ValidationError("Enter a valid percentage between 0 and 100.")
        return pct

    def clean_aadhaar_number(self):
        aadhaar = (self.cleaned_data.get("aadhaar_number") or "").strip()

        if not aadhaar:
            raise forms.ValidationError("Aadhaar number is required.")

        if not aadhaar.isdigit() or len(aadhaar) != 12 or aadhaar[0] == '0':
            raise forms.ValidationError(
                "Aadhaar number must be 12 digits and cannot start with 0."
            )

        return aadhaar

    def clean_mobile_number(self):
        mobile = (self.cleaned_data.get("mobile_number") or "").strip()
        if not mobile:
            raise forms.ValidationError("Mobile number is required.")
        if not mobile.isdigit() or len(mobile) != 10 or mobile[0] == '0':
            raise forms.ValidationError(
                "Number must be 10 digits and cannot start with 0."
            )
        return mobile

    def clean_alternative_mobile(self):
        alt_mobile = (self.cleaned_data.get("alternative_mobile") or "").strip()
        
        if alt_mobile:
            if not alt_mobile.isdigit():
                raise forms.ValidationError(
                    "Number must be 10 digits and cannot start with 0."
                )
            
            if len(alt_mobile) != 10:
                raise forms.ValidationError(
                    "Number must be 10 digits and cannot start with 0."
                )
            
            if alt_mobile[0] == '0':
                raise forms.ValidationError(
                    "Number must be 10 digits and cannot start with 0."
                )
        
        return alt_mobile

    def validate_name_field(self, value):
        if not value:
            raise forms.ValidationError("This field is required.")
        value = value.strip()
        if len(value) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        if len(value) > 150:
            raise forms.ValidationError("Name cannot exceed 150 characters.")
        if not all(x.isalpha() or x.isspace() for x in value):
            raise forms.ValidationError("Only alphabets and spaces are allowed. Numbers and special characters are not permitted.")
        return value

    def clean_full_name(self):
        return self.validate_name_field(self.cleaned_data.get('full_name', ''))

    def clean_father_name(self):
        return self.validate_name_field(self.cleaned_data.get('father_name', ''))

    def clean_mother_name(self):
        return self.validate_name_field(self.cleaned_data.get('mother_name', ''))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        email = email.strip().lower()
        if '@' not in email or '.' not in email:
            raise forms.ValidationError("Enter a valid email address.")
        return email

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode') or ''
        pincode = pincode.strip()
        if not pincode:
            # allow blank here; model validator will enforce if needed
            return pincode
        if not pincode.isdigit() or len(pincode) != 6:
            raise forms.ValidationError("Enter a valid 6-digit pincode.")
        return pincode

    def clean_abc_id(self):
        abc_id = self.cleaned_data.get('abc_id')
        if abc_id:
            abc_id = abc_id.strip()
            if not abc_id.isdigit() or len(abc_id) != 12:
                raise forms.ValidationError("Enter a valid 12-digit ABC ID (Apaar ID).")
        return abc_id

    def clean_institution(self):
        from masterdata.models import EducationalInstitution
        institution = self.cleaned_data.get('institution')
        other_institution = self.data.get('other_institution')

        if institution == 'Other' or not institution:
            if other_institution and other_institution.strip():
                institution = other_institution.strip()
            else:
                raise forms.ValidationError("Please enter your educational institution name.")

        institution = institution.strip()
        if institution == 'Other':
            raise forms.ValidationError("Please enter your educational institution name.")

        if len(institution) < 3:
            raise forms.ValidationError("Institution name must be at least 3 characters long.")
        if len(institution) > 200:
            raise forms.ValidationError("Institution name cannot exceed 200 characters.")

        inst_obj = EducationalInstitution.get_or_create_institution(institution)
        if inst_obj:
            return inst_obj.name

        return institution

    def clean_hall_ticket_number(self):
        hall_ticket = self.cleaned_data.get('hall_ticket_number')
        if not hall_ticket:
            raise forms.ValidationError("Hall ticket number is required.")
        hall_ticket = hall_ticket.strip()
        if len(hall_ticket) > 50:
            raise forms.ValidationError("Hall ticket number cannot exceed 50 characters.")
        return hall_ticket

    def clean_communication_address(self):
        address = self.cleaned_data.get('communication_address')
        if not address:
            raise forms.ValidationError("Communication address is required.")
        address = address.strip()
        if len(address) < 10:
            raise forms.ValidationError("Address must be at least 10 characters long.")
        return address

    def clean_dob(self):
        import datetime
        dob = self.cleaned_data.get('dob')
        if not dob:
            raise forms.ValidationError("Date of Birth is required.")
        if dob > datetime.date.today():
            raise forms.ValidationError("Date of Birth cannot be in the future.")
        # Check if person is at least 10 years old
        min_age_date = datetime.date.today() - datetime.timedelta(days=365*10)
        if dob > min_age_date:
            raise forms.ValidationError("You must be at least 10 years old.")
        return dob

    def clean_distinguishing_mark(self):
        mark = self.cleaned_data.get('distinguishing_mark')
        if not mark:
            raise forms.ValidationError("Distinguishing Mark is mandatory.")
        
        mark = mark.strip()
        if len(mark) < 5 or len(mark) > 100:
            raise forms.ValidationError("Length must be between 5 and 100 characters.")
            
        if not all(x.isalpha() or x.isspace() for x in mark):
            raise forms.ValidationError("Only alphabetic characters and spaces are allowed. Numbers and special characters are not permitted.")
            
        return mark

    def clean_year_of_passing(self):
        import datetime
        yop = self.cleaned_data.get('year_of_passing')
        if not yop:
            raise forms.ValidationError("Year of passing is required.")
        
        current_year = datetime.datetime.now().year
        if yop < 1950 or yop > current_year + 5:
            raise forms.ValidationError(f"Year of passing must be between 1950 and {current_year + 5}.")
        
        return yop

    def clean_annual_income(self):
        income = self.cleaned_data.get('annual_income')
        if income is not None:
            if income < 0:
                raise forms.ValidationError("Please enter a valid annual income.")
        return income

    def clean_registration_number(self):
        reg_num = self.cleaned_data.get('registration_number')
        if reg_num:
            reg_num = reg_num.strip()
            if len(reg_num) > 50:
                raise forms.ValidationError("Registration number cannot exceed 50 characters.")
        return reg_num

    def clean_nielit_registration_number(self):
        val = self.cleaned_data.get('nielit_registration_number')
        if val:
            val = val.strip()
            if len(val) > 50:
                raise forms.ValidationError("NIELIT Registration Number cannot exceed 50 characters.")
            import re
            if not re.match(r'^[A-Za-z0-9 -]*$', val):
                raise forms.ValidationError("Only letters, numbers, spaces, and hyphens (-) are allowed.")
        return val

    def clean_custom_stream(self):
        stream = self.cleaned_data.get('custom_stream')
        if stream:
            stream = stream.strip()
            if len(stream) < 2:
                raise forms.ValidationError("Stream must be at least 2 characters long.")
            if len(stream) > 100:
                raise forms.ValidationError("Stream cannot exceed 100 characters.")
        return stream

    def clean_batch_code(self):
        batch = self.cleaned_data.get('batch_code')
        if batch:
            batch = batch.strip()
            if len(batch) > 50:
                raise forms.ValidationError("Batch code cannot exceed 50 characters.")
        return batch

    def clean_area_village_name(self):
        area = self.cleaned_data.get('area_village_name')
        if area:
            area = area.strip()
            if len(area) < 2:
                raise forms.ValidationError("Area/Village name must be at least 2 characters long.")
            if len(area) > 255:
                raise forms.ValidationError("Area/Village name cannot exceed 255 characters.")
        return area
