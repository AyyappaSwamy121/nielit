import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from masterdata.models import (
    Country, State, District, Religion, MaritalStatus, ExServiceStatus, 
    Community, Occupation, Qualification, YearOfStudy, Program, ApplicationStatus
)

def populate():
    # ApplicationStatus
    for idx, (name, code) in enumerate([
        ('Pending', 'PENDING'), ('Approved', 'APPROVED'), 
        ('Rejected', 'REJECTED'), ('Correction', 'CORRECTION')
    ]):
        ApplicationStatus.objects.get_or_create(name=name, code=code, display_order=idx)
        
    # Country, State, District
    india, _ = Country.objects.get_or_create(name='India', code='IN', display_order=1)
    ap, _ = State.objects.get_or_create(name='Andhra Pradesh', code='AP', country=india, display_order=1)
    ts, _ = State.objects.get_or_create(name='Telangana', code='TS', country=india, display_order=2)
    District.objects.get_or_create(name='Hyderabad', code='HYD', state=ts, display_order=1)
    District.objects.get_or_create(name='Visakhapatnam', code='VSK', state=ap, display_order=2)

    # Religion
    for idx, r in enumerate(['Hindu', 'Muslim', 'Christian', 'Sikh', 'Jain', 'Buddhist', 'Other']):
        Religion.objects.get_or_create(name=r, display_order=idx)

    # Marital Status
    for idx, m in enumerate(['Single', 'Married', 'Divorced', 'Widowed']):
        MaritalStatus.objects.get_or_create(name=m, display_order=idx)

    # Ex-Service Man
    for idx, e in enumerate(['Yes', 'No']):
        ExServiceStatus.objects.get_or_create(name=e, display_order=idx)

    # Community
    for idx, (c, s) in enumerate([
        ('Scheduled Caste (SC)', 'SC'), ('Scheduled Tribe (ST)', 'ST'), 
        ('OBC', 'OBC'), ('General', 'General')
    ]):
        Community.objects.get_or_create(name=c, defaults={'short_name': s, 'display_order': idx})

    # Occupation
    for idx, o in enumerate(['Student', 'Employed', 'Unemployed', 'Self Employed', 'Housewife', 'Other']):
        Occupation.objects.get_or_create(name=o, display_order=idx)

    # Qualification
    quals = [
        'B.Tech Civil Engineering', 'B.Tech Electrical & Electronics Engineering',
        'B.Tech Electronics & Communication Engineering', 'B.Tech Computer Science & Engineering',
        'B.Tech CSE (AIML)', 'B.Tech CSE (AIDS)',
        'B.Tech Mechanical Engineering', 'B.Tech IT',
        'M.Tech CE – Structural Engineering', 'M.Tech Digital Electronics & Communication Systems',
        'M.Tech Machine Design', 'M.Tech Computer Science & Engineering',
        'MBA', 'PhD', 'Degree', 'Other'
    ]
    for idx, q in enumerate(quals):
        Qualification.objects.get_or_create(name=q, defaults={'display_order': idx})

    # Year Of Study
    years = ['1', '2', '3', '4', 'Completed', 'Faculty']
    for idx, y in enumerate(years):
        YearOfStudy.objects.get_or_create(name=y, defaults={'display_order': idx})

    # Program
    Program.objects.get_or_create(name='Embedded & SoC Designer', defaults={'display_order': 1})
    
    print("Master Data populated successfully.")

if __name__ == '__main__':
    populate()
