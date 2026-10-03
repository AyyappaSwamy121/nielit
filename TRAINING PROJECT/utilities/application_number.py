from django.utils import timezone
from registrations.models import StudentApplication
from django.db import transaction

def generate_application_number():
    """
    Generates a unique application number automatically.
    Example: Council for Skills and Competencies202600001
    """
    year = timezone.now().year
    prefix = f'CSC{year}'
    
    with transaction.atomic():
        # Lock the row to prevent race conditions when finding the last app
        last_app = StudentApplication.objects.select_for_update().filter(
            application_number__startswith=prefix
        ).order_by('id').last()
        
        if last_app and last_app.application_number:
            try:
                seq = int(last_app.application_number[-5:]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
            
        return f'{prefix}{seq:05d}'

