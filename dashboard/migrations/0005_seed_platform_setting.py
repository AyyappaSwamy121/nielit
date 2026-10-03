from django.db import migrations


MAPPING = [
    ('portal_name', 'portal_name', ''),
    ('organization_name', 'organization_name', ''),
    ('contact_email', 'contact_email', ''),
    ('contact_phone', 'contact_phone', ''),
    ('logo', 'logo', ''),
    ('favicon', 'favicon', ''),
    ('auto_save_interval', 'auto_save_interval', '30'),
]


def seed_platform_setting(apps, schema_editor):
    SystemSetting = apps.get_model('dashboard', 'SystemSetting')
    PlatformSetting = apps.get_model('dashboard', 'PlatformSetting')

    if PlatformSetting.objects.exists():
        return

    def lookup(key, default):
        try:
            obj = SystemSetting.objects.get(key=key)
            return obj.value
        except SystemSetting.DoesNotExist:
            return default

    obj = PlatformSetting()
    obj.portal_name = lookup('portal_name', 'CSC Admin Portal') or 'CSC Admin Portal'
    obj.organization_name = lookup('organization_name', 'Council for Skills and Competencies') or 'Council for Skills and Competencies'
    obj.contact_email = lookup('contact_email', '') or ''
    obj.contact_phone = lookup('contact_phone', '') or ''
    obj.auto_save_interval = int(lookup('auto_save_interval', '30') or '30')
    for source_key, field_name, default in MAPPING:
        value = lookup(source_key, default)
        if value and field_name in ('logo', 'favicon'):
            # The SystemSetting value is an existing storage path (e.g. settings/logo.png).
            # Reuse that file in place so no copy is required.
            setattr(obj, field_name, value)
    obj.save()


def unseed_platform_setting(apps, schema_editor):
    PlatformSetting = apps.get_model('dashboard', 'PlatformSetting')
    PlatformSetting.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_platformsetting'),
    ]

    operations = [
        migrations.RunPython(seed_platform_setting, unseed_platform_setting),
    ]
