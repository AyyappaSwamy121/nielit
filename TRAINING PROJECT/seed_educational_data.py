import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from masterdata.models import Qualification, TrainingPartner, BatchCode

def seed():
    qualifications = [
        "Computer Science and Engineering (CSE)", "Artificial Intelligence and Data Science (AI & DS)",
        "Artificial Intelligence and Machine Learning (AI & ML)", "Information Technology (IT)",
        "Electronics and Communication Engineering (ECE)", "Electrical and Electronics Engineering (EEE)",
        "Mechanical Engineering", "Civil Engineering", "Chemical Engineering",
        "Aeronautical Engineering", "Aerospace Engineering", "Automobile Engineering",
        "Mining Engineering", "Metallurgical Engineering", "Agricultural Engineering",
        "Petroleum Engineering", "Biotechnology Engineering", "Textile Engineering",
        "Production Engineering", "Mechatronics Engineering",
        "Diploma in Computer Engineering", "Diploma in Mechanical Engineering",
        "Diploma in Civil Engineering", "Diploma in Electrical Engineering",
        "Diploma in Electronics Engineering", "Diploma in Automobile Engineering",
        "Diploma in Information Technology", "Diploma in Mining Engineering",
        "B.Sc Mathematics", "B.Sc Physics", "B.Sc Chemistry", "B.Sc Computer Science",
        "B.Sc Electronics", "B.Sc Biotechnology", "B.Sc Microbiology", "B.Sc Agriculture",
        "B.Com", "M.Com", "BBA", "MBA", "BA", "MA", "BSW", "BCA", "MCA",
        "MBBS", "BDS", "B.Pharmacy", "M.Pharmacy", "Nursing", "Physiotherapy",
        "LLB", "LLM", "B.Ed", "M.Ed", "M.Tech", "M.Sc", "Ph.D", "Other"
    ]
    
    print("Seeding Qualifications...")
    for q in qualifications:
        Qualification.objects.get_or_create(name=q)
        
    print("Seeding Training Partner...")
    tp, _ = TrainingPartner.objects.get_or_create(name="Council For Skills And Competencies (CSC)")
    
    print("Seeding Batch Code...")
    BatchCode.objects.get_or_create(code="BATCH-CSC-2026-01", training_partner=tp)
    
    print("Seeding complete.")

if __name__ == '__main__':
    seed()
