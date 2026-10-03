from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0018_studentapplication_is_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentapplication',
            name='nielit_registration_number',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
