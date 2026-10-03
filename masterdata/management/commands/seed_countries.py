from django.core.management.base import BaseCommand
from masterdata.models import Country

class Command(BaseCommand):
    help = 'Seeds the database with standard countries'

    def handle(self, *args, **kwargs):
        countries = [
            {'name': 'India', 'code': 'IND', 'iso_code': 'IND', 'display_order': 1},
            {'name': 'Nepal', 'code': 'NPL', 'iso_code': 'NPL', 'display_order': 2},
            {'name': 'Bangladesh', 'code': 'BGD', 'iso_code': 'BGD', 'display_order': 3},
            {'name': 'Bhutan', 'code': 'BTN', 'iso_code': 'BTN', 'display_order': 4},
            {'name': 'Sri Lanka', 'code': 'LKA', 'iso_code': 'LKA', 'display_order': 5},
            {'name': 'Maldives', 'code': 'MDV', 'iso_code': 'MDV', 'display_order': 6},
            {'name': 'Other', 'code': 'OTH', 'iso_code': 'OTH', 'display_order': 99},
        ]

        count = 0
        for data in countries:
            obj, created = Country.objects.get_or_create(
                name=data['name'],
                defaults={
                    'code': data['code'],
                    'iso_code': data['iso_code'],
                    'display_order': data['display_order']
                }
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} new countries.'))
