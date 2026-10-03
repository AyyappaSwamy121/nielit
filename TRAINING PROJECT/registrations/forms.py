from django import forms
from django.core.exceptions import ValidationError
from .models import StudentApplication
from masterdata.models import District, State, Country

class StudentApplicationForm(forms.ModelForm):
    class Meta:
        model = StudentApplication
        fields = [
            'full_name', 'father_name', 'mother_name', 'dob', 'gender',
            'religion', 'marital_status', 'community', 'ex_serviceman',
            'occupation', 'category', 'nationality', 'physically_handicapped',
            'annual_income', 'mobile_number', 'alternative_mobile', 'email',
            'communication_address', 'country', 'state', 'district', 'pincode',
            'institution', 'hall_ticket_number', 'registration_number',
            'applying_qualification', 'qualification', 'custom_stream',
            'program_opting',
            'mode_of_qualification', 'completion_status', 'percentage',
            'year_of_passing', 'training_partner', 'batch_code',
            'aadhaar_number', 'abc_id', 'distinguishing_mark', 'consent_given'
        ]

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
        if 'program_opting' not in cleaned_data or not cleaned_data['program_opting']:
            self.add_error('program_opting', 'This field is required.')
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
        aadhaar = self.cleaned_data.get("aadhaar_number", "").strip()

        if not aadhaar.isdigit():
            raise forms.ValidationError(
                "Aadhaar number must contain numbers only."
            )

        if len(aadhaar) != 12:
            raise forms.ValidationError(
                "Aadhaar number must contain exactly 12 digits."
            )

        return aadhaar

    def validate_name_field(self, value):
        if value:
            value = value.strip()
            if not all(x.isalpha() or x.isspace() for x in value):
                raise forms.ValidationError("Only alphabets and spaces are allowed. Numbers and special characters are not permitted.")
        return value

    def clean_full_name(self):
        return self.validate_name_field(self.cleaned_data.get('full_name', ''))

    def clean_father_name(self):
        return self.validate_name_field(self.cleaned_data.get('father_name', ''))

    def clean_mother_name(self):
        return self.validate_name_field(self.cleaned_data.get('mother_name', ''))

    def clean_dob(self):
        import datetime
        dob = self.cleaned_data.get('dob')
        if dob and dob > datetime.date.today():
            raise forms.ValidationError("Date of Birth cannot be in the future.")
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

    def clean_annual_income(self):
        income = self.cleaned_data.get('annual_income')
        if income is not None:
            if income < 0:
                raise forms.ValidationError("Please enter a valid annual income.")
        return income
