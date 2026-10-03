import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from masterdata.models import Occupation

occupations = [
    "Student",
    "Employee",
    "Government Employee",
    "Private Employee",
    "Self Employed",
    "faculty",
    "Other"
]

for name in occupations:
    obj, created = Occupation.objects.get_or_create(name=name)
    if created:
        print(f"Created Occupation: {name}")

print("Occupation Master Data verification complete.")
