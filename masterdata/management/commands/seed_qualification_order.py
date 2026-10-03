from django.core.management.base import BaseCommand
from masterdata.models import Qualification

class Command(BaseCommand):
    help = 'Seeds or updates the exact display order for all Qualification records'

    def handle(self, *args, **kwargs):
        requested_order = [
            '12th or equivalent',
            'Diploma in Computer Engineering',
            'Diploma in Mechanical Engineering',
            'Diploma in Civil Engineering',
            'Diploma in Electrical Engineering',
            'Diploma in Electronics Engineering',
            'Diploma in Automobile Engineering',
            'Diploma in Information Technology',
            'Diploma in Mining Engineering',
            '2yrs of 3 yr dip in ECE/EE/CS/IT and allied branches after 10th',
            'B.Tech Civil Engineering',
            'B.Tech Computer Science & Engineering',
            'B.Tech CSE (Artificial Intelligence & Data Science)',
            'B.Tech CSE (Artificial Intelligence & Machine Learning)',
            'B.Tech Electrical & Electronics Engineering',
            'B.Tech Electronics & Communication Engineering',
            'B.Tech Mechanical Engineering',
            'B.Tech Information Technology',
            'B.Tech IT',
            'B.Tech Chemical Engineering',
            'B.Tech Aeronautical Engineering',
            'B.Tech Aerospace Engineering',
            'B.Tech Automobile Engineering',
            'B.Tech Mining Engineering',
            'B.Tech Metallurgical Engineering',
            'B.Tech Agricultural Engineering',
            'B.Tech Petroleum Engineering',
            'B.Tech Biotechnology Engineering',
            'B.Tech Textile Engineering',
            'B.Tech Production Engineering',
            'B.Tech Mechatronics Engineering',
            'B.Sc Mathematics',
            'B.Sc Physics',
            'B.Sc Chemistry',
            'B.Sc Computer Science',
            'B.Sc Electronics',
            'B.Sc Biotechnology',
            'B.Sc Microbiology',
            'B.Sc Agriculture',
            'B.Com',
            'BBA',
            'BA',
            'BSW',
            'BCA',
            'MBBS',
            'BDS',
            'B.Pharmacy',
            'Nursing',
            'Physiotherapy',
            'LLB',
            'B.Ed',
            'M.Com',
            'MA',
            'MCA',
            'M.Pharmacy',
            'M.Ed',
            'M.Tech',
            'M.Sc',
            'MBA',
            'LLM',
            'Ph.D',
            'PhD',
            'Degree',
            'Diploma',
            'Other'
        ]

        count = 0
        for idx, name in enumerate(requested_order, start=1):
            q = Qualification.objects.filter(name=name).first()
            if q:
                q.display_order = idx
                q.save()
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully updated display_order for {count} Qualification records.'))
