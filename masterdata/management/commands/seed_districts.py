from django.core.management.base import BaseCommand
from masterdata.models import State, District

class Command(BaseCommand):
    help = 'Seeds the database with districts for Indian states'

    def handle(self, *args, **kwargs):
        districts_data = {
            "Andhra Pradesh": [
                "Anakapalli", "Anantapur", "Annamayya", "Bapatla", "Chittoor", 
                "Dr. B.R. Ambedkar Konaseema", "East Godavari", "Eluru", "Guntur", 
                "Kakinada", "Krishna", "Kurnool", "Nandyal", "NTR", "Palnadu", 
                "Parvathipuram Manyam", "Prakasam", "SPSR Nellore", "Srikakulam", 
                "Sri Sathya Sai", "Tirupati", "Visakhapatnam", "Vizianagaram", 
                "West Godavari", "YSR Kadapa"
            ],
            "Telangana": [
                "Adilabad", "Bhadradri Kothagudem", "Hyderabad", "Jagtial", "Jangaon",
                "Jayashankar Bhupalpally", "Jogulamba Gadwal", "Kamareddy", "Karimnagar",
                "Khammam", "Komaram Bheem Asifabad", "Mahabubabad", "Mahabubnagar",
                "Mancherial", "Medak", "Medchal-Malkajgiri", "Mulugu", "Nagarkurnool",
                "Nalgonda", "Narayanpet", "Nirmal", "Nizamabad", "Peddapalli", "Rajanna Sircilla",
                "Rangareddy", "Sangareddy", "Siddipet", "Suryapet", "Vikarabad", "Wanaparthy",
                "Warangal (Rural)", "Warangal (Urban)", "Yadadri Bhuvanagiri"
            ],
            "Karnataka": [
                "Bagalkot", "Ballari (Bellary)", "Belagavi (Belgaum)", "Bengaluru (Bangalore) Rural",
                "Bengaluru (Bangalore) Urban", "Bidar", "Chamarajanagar", "Chikballapur",
                "Chikkamagaluru (Chikmagalur)", "Chitradurga", "Dakshina Kannada", "Davangere",
                "Dharwad", "Gadag", "Hassan", "Haveri", "Kalaburagi (Gulbarga)", "Kodagu",
                "Kolar", "Koppal", "Mandya", "Mysuru (Mysore)", "Raichur", "Ramanagara",
                "Shivamogga (Shimoga)", "Tumakuru (Tumkur)", "Udupi", "Uttara Kannada (Karwar)",
                "Vijayapura (Bijapur)", "Yadgir"
            ]
        }

        count = 0
        for state_name, districts in districts_data.items():
            try:
                state = State.objects.get(name=state_name)
                for i, d_name in enumerate(districts):
                    obj, created = District.objects.get_or_create(
                        name=d_name,
                        state=state,
                        defaults={
                            'code': d_name[:3].upper() + str(i),
                            'display_order': i + 1
                        }
                    )
                    if created:
                        count += 1
            except State.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"State {state_name} not found. Skipping its districts."))

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} new districts.'))
