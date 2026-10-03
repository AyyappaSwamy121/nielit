import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from registrations.models import StudentApplication

apps = StudentApplication.objects.all()

cleaned_count = 0
for app in apps:
    modified = False
    
    if app.full_name and not re.match(r"^[a-zA-Z\s]+$", app.full_name):
        app.full_name = re.sub(r'[^a-zA-Z\s]', '', app.full_name).strip()
        modified = True
        
    if app.father_name and not re.match(r"^[a-zA-Z\s]+$", app.father_name):
        app.father_name = re.sub(r'[^a-zA-Z\s]', '', app.father_name).strip()
        modified = True
        
    if app.mother_name and not re.match(r"^[a-zA-Z\s]+$", app.mother_name):
        app.mother_name = re.sub(r'[^a-zA-Z\s]', '', app.mother_name).strip()
        modified = True
        
    if modified:
        app.save(update_fields=['full_name', 'father_name', 'mother_name'])
        cleaned_count += 1

print(f"Cleaned {cleaned_count} records.")
