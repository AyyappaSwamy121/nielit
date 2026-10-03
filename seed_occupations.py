import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from masterdata.models import Occupation

occupations = [
    "Choose",
    "Student",
    "Employed",
    "Unemployed",
    "Selfemployed",
    "Housewife",
    "Other"
]

for name in occupations:
    obj, created = Occupation.objects.get_or_create(name=name)
    if created:
        print(f"Created Occupation: {name}")

print("Occupation Master Data verification complete.")
