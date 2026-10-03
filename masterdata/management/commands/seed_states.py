from django.core.management.base import BaseCommand
from masterdata.models import Country, State

class Command(BaseCommand):
    help = 'Seeds the database with Indian states and union territories'

    def handle(self, *args, **kwargs):
        india, _ = Country.objects.get_or_create(name='India', defaults={'code': 'IND', 'iso_code': 'IND'})
        
        states = [
            ("Andhra Pradesh", "AP"),
            ("Arunachal Pradesh", "AR"),
            ("Assam", "AS"),
            ("Bihar", "BR"),
            ("Chhattisgarh", "CG"),
            ("Goa", "GA"),
            ("Gujarat", "GJ"),
            ("Haryana", "HR"),
            ("Himachal Pradesh", "HP"),
            ("Jharkhand", "JH"),
            ("Karnataka", "KA"),
            ("Kerala", "KL"),
            ("Madhya Pradesh", "MP"),
            ("Maharashtra", "MH"),
            ("Manipur", "MN"),
            ("Meghalaya", "ML"),
            ("Mizoram", "MZ"),
            ("Nagaland", "NL"),
            ("Odisha", "OD"),
            ("Punjab", "PB"),
            ("Rajasthan", "RJ"),
            ("Sikkim", "SK"),
            ("Tamil Nadu", "TN"),
            ("Telangana", "TS"),
            ("Tripura", "TR"),
            ("Uttar Pradesh", "UP"),
            ("Uttarakhand", "UK"),
            ("West Bengal", "WB"),
            # Union Territories
            ("Andaman and Nicobar Islands", "AN"),
            ("Chandigarh", "CH"),
            ("Dadra and Nagar Haveli and Daman and Diu", "DH"),
            ("Delhi", "DL"),
            ("Jammu and Kashmir", "JK"),
            ("Ladakh", "LA"),
            ("Lakshadweep", "LD"),
            ("Puducherry", "PY")
        ]

        count = 0
        for i, (name, code) in enumerate(states):
            obj, created = State.objects.get_or_create(
                name=name,
                defaults={
                    'code': code,
                    'country': india,
                    'display_order': i + 1
                }
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} new states/UTs.'))
