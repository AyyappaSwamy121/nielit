# Generated data migration for EducationalInstitution master

from django.db import migrations

INSTITUTIONS = [
    "CMR Engineering College",
    "CMR College of Engineering & Technology",
    "CMR Institute of Technology",
    "Vardhaman College of Engineering",
    "SRK Institute of Technology",
    "Vijaya Institute of Technology for Women",
    "Narasaraopeta Engineering College",
    "Rajiv Gandhi University of Knowledge Technologies - Nuzvid",
    "Rajiv Gandhi University of Knowledge Technologies - RK Valley",
    "Rajiv Gandhi University of Knowledge Technologies - Ongole",
    "Rajiv Gandhi University of Knowledge Technologies - Srikakulam",
    "R.V.R. & J.C. College of Engineering",
    "Bapatla Women's Engineering College",
    "Pragati Engineering College",
    "Gayatri Vidya Parishad College of Engineering",
    "Gayatri Vidya Parishad College of Engineering for Women",
    "Gayatri Vidya Parishad College for Degree and PG Courses",
    "Ravindra College of Engineering for Women",
]


def seed_institutions(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    EducationalInstitution = apps.get_model('masterdata', 'EducationalInstitution')
    for order, name in enumerate(INSTITUTIONS, start=1):
        clean_name = name.strip()
        # Idempotent: check existing normalized name to prevent duplicates
        existing = EducationalInstitution.objects.using(db_alias).filter(name__iexact=clean_name).first()
        if not existing:
            EducationalInstitution.objects.using(db_alias).create(
                name=clean_name,
                display_order=order,
                is_active=True,
            )


def reverse_institutions(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    EducationalInstitution = apps.get_model('masterdata', 'EducationalInstitution')
    EducationalInstitution.objects.using(db_alias).filter(name__in=INSTITUTIONS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0005_educationalinstitution'),
    ]

    operations = [
        migrations.RunPython(seed_institutions, reverse_code=reverse_institutions),
    ]
