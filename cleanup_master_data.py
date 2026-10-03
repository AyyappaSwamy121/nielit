import os
import django
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from masterdata.models import YearOfStudy
from registrations.models import StudentApplication

def cleanup():
    with transaction.atomic():
        # 1. Ensure Canonical YearOfStudy records exist
        y1, _ = YearOfStudy.objects.get_or_create(name='1', defaults={'display_order': 0})
        y2, _ = YearOfStudy.objects.get_or_create(name='2', defaults={'display_order': 1})
        y3, _ = YearOfStudy.objects.get_or_create(name='3', defaults={'display_order': 2})
        y4, _ = YearOfStudy.objects.get_or_create(name='4', defaults={'display_order': 3})
        completed, _ = YearOfStudy.objects.get_or_create(name='Completed', defaults={'display_order': 4})
        faculty, _ = YearOfStudy.objects.get_or_create(name='Faculty', defaults={'display_order': 5})

        # 2. Map existing duplicate records
        mapping = {
            'First Year': y1,
            'Second Year': y2,
            'Third Year': y3,
            'Fourth Year': y4
        }
        
        for old_val, canon in mapping.items():
            dupes = YearOfStudy.objects.filter(name__iexact=old_val)
            if dupes.exists():
                for dupe in dupes:
                    apps = StudentApplication.objects.filter(year_of_study=dupe)
                    apps_count = apps.count()
                    apps.update(year_of_study=canon)
                    print(f"Mapped {apps_count} apps from '{dupe.name}' to '{canon.name}'")
                dupes.delete()
                print(f"Deleted duplicate '{old_val}' records.")

    print("Cleanup Complete.")

if __name__ == '__main__':
    cleanup()
