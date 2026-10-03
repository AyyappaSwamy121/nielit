from django.conf import settings
from django.db import models
from django.utils import timezone


class SystemSetting(models.Model):
    key = models.CharField(max_length=150, unique=True)
    value = models.TextField(blank=True, default='')
    category = models.CharField(max_length=100, blank=True, default='')
    description = models.CharField(max_length=500, blank=True, default='')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='system_setting_updates',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'key']
        permissions = [
            ("view_platform_settings", "Can view Platform Settings"),
            ("change_platform_settings", "Can change Platform Settings"),
        ]

    def __str__(self):
        return f"{self.key} ({self.category})"

    @classmethod
    def get_value(cls, key, default=''):
        try:
            obj = cls.objects.get(key=key)
            return obj.value
        except cls.DoesNotExist:
            return default


class PlatformSetting(models.Model):
    """Singleton configuration row that drives branding and core behavior."""

    portal_name = models.CharField(max_length=255, default='CSC Admin Portal', blank=True)
    organization_name = models.CharField(
        max_length=255,
        default='Council for Skills and Competencies',
        blank=True,
    )
    contact_email = models.EmailField(max_length=255, blank=True, default='')
    contact_phone = models.CharField(max_length=30, blank=True, default='')
    support_email = models.EmailField(max_length=255, blank=True, default='')
    support_phone = models.CharField(max_length=30, blank=True, default='')
    logo = models.FileField(upload_to='platform/logo/', blank=True, null=True)
    favicon = models.FileField(upload_to='platform/favicon/', blank=True, null=True)
    portal_description = models.TextField(blank=True, default='')
    timezone = models.CharField(max_length=100, default='UTC', blank=True)
    date_format = models.CharField(max_length=50, default='d M Y', blank=True)
    maintenance_mode = models.BooleanField(default=False)
    auto_save_enabled = models.BooleanField(default=True)
    auto_save_interval = models.PositiveIntegerField(default=30)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='platform_setting_updates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("view_platform_settings", "Can view Platform Settings"),
            ("change_platform_settings", "Can change Platform Settings"),
        ]

    def __str__(self):
        return self.portal_name or self.organization_name or "Platform Settings"

    def save(self, *args, **kwargs):
        if not self.pk:
            PlatformSetting.objects.all().delete()
        return super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls()
            obj.save()
        return obj

    def has_logo(self):
        return bool(self.logo)

    def has_favicon(self):
        return bool(self.favicon)


class BackupJob(models.Model):
    BACKUP_TYPES = [
        ("database", "Database"),
        ("media", "Media / Documents"),
        ("full", "Full System"),
    ]
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPES)
    file = models.FileField(upload_to="backups/", blank=True, null=True)
    file_size = models.PositiveBigIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='backup_jobs',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("view_backup_center", "Can view the Backup & Restore center"),
            ("create_backup", "Can create backups"),
            ("download_backup", "Can download backups"),
            ("restore_backup", "Can restore the system from a backup"),
        ]

    @property
    def display_id(self):
        return f"BK-{self.pk:04d}" if self.pk else "BK-____"

    @property
    def backup_type_label(self):
        for value, label in self.BACKUP_TYPES:
            if value == self.backup_type:
                return label
        return self.backup_type

    @property
    def status_label(self):
        for value, label in self.STATUS_CHOICES:
            if value == self.status:
                return label
        return self.status

    @property
    def filename(self):
        if self.file:
            import os
            return os.path.basename(self.file.name)
        return f"backup_{self.display_id}"

    def __str__(self):
        return f"{self.display_id} {self.backup_type} - {self.status}"


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)
    detail = models.TextField(blank=True, default='')
    application_ids = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} by {self.user or 'anonymous'} at {self.created_at}"


class ExportJob(models.Model):
    EXPORT_TYPES = [
        ("applications", "Student Applications"),
        ("students", "Student Directory"),
        ("documents", "Documents"),
        ("reports", "Application Reports"),
        ("master_data", "Master Data"),
        ("audit_logs", "Audit Logs"),
    ]

    FORMATS = [
        ("csv", "CSV"),
        ("xlsx", "Excel"),
        ("pdf", "PDF"),
        ("zip", "ZIP"),
    ]

    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    export_type = models.CharField(max_length=50, choices=EXPORT_TYPES)
    file_format = models.CharField(max_length=20, choices=FORMATS)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='export_jobs',
    )

    filters = models.JSONField(default=dict, blank=True)

    record_count = models.PositiveIntegerField(default=0)

    file = models.FileField(upload_to="exports/", blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("view_export_center", "Can view the Export Center"),
            ("export_applications", "Can export applications"),
            ("export_student_data", "Can export student data"),
            ("export_documents", "Can export documents"),
            ("export_master_data", "Can export master data"),
            ("export_audit_logs", "Can export audit logs"),
            ("download_export_history", "Can download export history"),
        ]

    @property
    def display_id(self):
        return f"EXP-{self.pk:04d}" if self.pk else "EXP-____"

    @property
    def export_type_label(self):
        for value, label in self.EXPORT_TYPES:
            if value == self.export_type:
                return label
        return self.export_type

    @property
    def format_label(self):
        for value, label in self.FORMATS:
            if value == self.file_format:
                return label
        return self.file_format

    @property
    def status_label(self):
        for value, label in self.STATUS_CHOICES:
            if value == self.status:
                return label
        return self.status

    @property
    def is_expired(self):
        return bool(self.expires_at) and self.expires_at < timezone.now()

    @property
    def filename(self):
        if self.file:
            import os
            return os.path.basename(self.file.name)
        return f"export_{self.display_id}.{self.file_format or 'csv'}"

    def __str__(self):
        return f"{self.display_id} {self.export_type}/{self.file_format} - {self.status}"


class FormSection(models.Model):
    """A collapsible section of the student registration form."""

    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=60, blank=True, default='view_module')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return self.name


class FormFieldConfiguration(models.Model):
    """Database-driven configuration for one field of the student form.

    This is the single source of truth for labels, placeholders, validation,
    visibility, ordering and options. Values are rendered and validated from
    here - never duplicated in templates or views.
    """

    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('textarea', 'Textarea'),
        ('email', 'Email'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('select', 'Dropdown'),
        ('radio', 'Radio'),
        ('checkbox', 'Checkbox'),
        ('file', 'File Upload'),
        ('phone', 'Phone'),
        ('aadhaar', 'Aadhaar'),
        ('pincode', 'Pincode'),
    ]
    OPTIONS_SOURCE_CHOICES = [
        ('options', 'Configured Options'),
        ('masterdata', 'Master Data Table'),
    ]
    SPECIAL_VALIDATORS = [
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('aadhaar', 'Aadhaar'),
        ('pincode', 'Pincode'),
        ('date', 'Date'),
        ('number', 'Number'),
        ('percentage', 'Percentage'),
        ('alphabetic', 'Alphabetic'),
        ('alphanumeric', 'Alphanumeric'),
        ('regex', 'Regex'),
    ]

    section = models.ForeignKey(FormSection, on_delete=models.PROTECT, related_name='fields')
    field_name = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='text')
    placeholder = models.CharField(max_length=255, blank=True, default='')
    help_text = models.TextField(blank=True, default='')
    required = models.BooleanField(default=False)
    visible = models.BooleanField(default=True)
    readonly = models.BooleanField(default=False)
    default_value = models.TextField(blank=True, default='')

    # Validation
    min_length = models.PositiveIntegerField(null=True, blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    min_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    regex_pattern = models.CharField(max_length=500, blank=True, default='')
    validator_type = models.CharField(max_length=30, blank=True, default='')

    # Options
    options_source = models.CharField(max_length=20, choices=OPTIONS_SOURCE_CHOICES, default='options')
    source_model = models.CharField(max_length=100, blank=True, default='')
    options = models.JSONField(default=list, blank=True)

    # File configuration
    allowed_file_types = models.JSONField(default=list, blank=True)
    max_file_size = models.PositiveIntegerField(null=True, blank=True, help_text='Maximum file size in KB')
    min_file_size = models.PositiveIntegerField(null=True, blank=True, help_text='Minimum file size in KB')
    image_min_width = models.PositiveIntegerField(null=True, blank=True)
    image_min_height = models.PositiveIntegerField(null=True, blank=True)

    # Messages / conditions
    validation_messages = models.JSONField(default=dict, blank=True)
    conditions = models.JSONField(default=list, blank=True)

    # Behaviour
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_conditional = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='form_field_updates',
    )

    class Meta:
        ordering = ['section__display_order', 'display_order', 'id']
        permissions = [
            ("view_form_builder", "Can view Form Builder"),
            ("change_form_builder", "Can change form configuration"),
        ]

    def __str__(self):
        return f"{self.label} ({self.field_name})"

    def get_options(self):
        return self.options if isinstance(self.options, list) else []


class FormFieldOption(models.Model):
    """Admin-managed option for a select/radio field."""

    field = models.ForeignKey(FormFieldConfiguration, on_delete=models.CASCADE, related_name='field_options')
    label = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.label} ({self.value})"


class FormConfigurationVersion(models.Model):
    """Immutable snapshot of the form configuration (draft/publish history)."""

    version = models.PositiveIntegerField(unique=True)
    label = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, default='published')
    changes = models.TextField(blank=True, default='')
    snapshot = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='form_config_versions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']

    def __str__(self):
        return f"Version {self.version} - {self.created_at}"
