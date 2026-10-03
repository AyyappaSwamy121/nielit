import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_person_name(value):
    if not value or len(value.strip()) < 2:
        raise ValidationError(_('Name must be at least 2 characters long.'))
    
    if len(value) > 100:
        raise ValidationError(_('Name cannot exceed 100 characters.'))
        
    # Allow only letters and spaces. No digits or special characters.
    if not re.match(r"^[a-zA-Z\s]+$", value):
        raise ValidationError(_('Only alphabets and spaces are allowed. Numbers and special characters are not permitted.'))

def validate_indian_mobile(value):
    if not value or not re.match(r"^[6-9]\d{9}$", value):
        raise ValidationError(_('Enter a valid 10-digit mobile number.'))

def validate_indian_pincode(value):
    if not value or not re.match(r"^\d{6}$", value):
        raise ValidationError(_('Enter a valid 6-digit pincode.'))

def validate_hall_ticket(value):
    if not value:
        raise ValidationError(_('Hall ticket number is required.'))
    if len(value) > 50:
        raise ValidationError(_('Hall ticket number cannot exceed 50 characters.'))
    if not re.match(r"^[a-zA-Z0-9\-\/]+$", value):
        raise ValidationError(_('Hall ticket number can only contain letters, numbers, hyphens, and slashes.'))

def validate_aadhaar(value):
    if not re.match(r'^\d{12}$', str(value)):
        raise ValidationError('Enter a valid 12-digit Aadhaar number.')

def validate_abc_id(value):
    if not re.match(r'^\d{12}$', str(value)):
        raise ValidationError('Enter a valid 12-digit ABC ID (Apaar ID).')

def validate_percentage(value):
    try:
        val = float(value)
        if val < 0 or val > 100:
            raise ValidationError('Enter a valid percentage between 0 and 100.')
    except ValueError:
        raise ValidationError('Enter a valid percentage between 0 and 100.')