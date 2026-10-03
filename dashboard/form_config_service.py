"""FormConfigurationService - the single reusable layer that reads the
database-driven form configuration and exposes it to every consumer:

- the student registration form (rendering)
- backend validation on submission
- file validation
- admin preview
- future APIs

The database (FormSection / FormFieldConfiguration / FormFieldOption) is the
single source of truth. Nothing here duplicates hard-coded rules.
"""

import mimetypes
import re
from pathlib import Path

from django.utils import timezone


class FormConfigurationService:
    """Reads and validates against the DB-driven form configuration."""

    # Maps source_model string to the masterdata model class.
    MASTERDATA_MODELS = None

    def _model_for(self, name):
        if self.MASTERDATA_MODELS is None:
            from masterdata import models as md
            self.MASTERDATA_MODELS = {
                'Country': md.Country,
                'State': md.State,
                'District': md.District,
                'Religion': md.Religion,
                'Qualification': md.Qualification,
                'Program': md.Program,
                'Occupation': md.Occupation,
                'Community': md.Community,
                'MaritalStatus': md.MaritalStatus,
                'ExServiceStatus': md.ExServiceStatus,
                'TrainingPartner': md.TrainingPartner,
                'EducationalInstitution': md.EducationalInstitution,
            }
        return self.MASTERDATA_MODELS.get(name)

    # ------------------------------------------------------------------ read
    def get_sections(self, active_only=True):
        from .models import FormSection
        qs = FormSection.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return list(qs)

    def get_fields(self, section=None, active_only=True, visible_only=False):
        from .models import FormFieldConfiguration
        qs = FormFieldConfiguration.objects.select_related('section').all()
        if section is not None:
            qs = qs.filter(section=section)
        if active_only:
            qs = qs.filter(is_active=True)
        if visible_only:
            qs = qs.filter(visible=True)
        return list(qs.order_by('display_order', 'id'))

    def get_field(self, field_name):
        from .models import FormFieldConfiguration
        try:
            return FormFieldConfiguration.objects.select_related('section').get(field_name=field_name)
        except FormFieldConfiguration.DoesNotExist:
            return None

    def get_fields_by_section(self, active_only=True, visible_only=False):
        """Return [{section, fields:[...]}] grouped in section order."""
        result = []
        for section in self.get_sections(active_only=active_only):
            fields = self.get_fields(
                section=section, active_only=active_only, visible_only=visible_only
            )
            if fields:
                result.append({'section': section, 'fields': fields})
        return result

    def get_visible_fields(self):
        return self.get_fields(visible_only=True)

    def get_required_fields(self):
        from .models import FormFieldConfiguration
        return list(
            FormFieldConfiguration.objects.filter(
                is_active=True, visible=True, required=True
            ).order_by('display_order', 'id')
        )

    def get_options(self, field):
        """Return a list of {value, label} for a select/radio field."""
        if field.options_source == 'masterdata' and field.source_model:
            model = self._model_for(field.source_model)
            if model is not None:
                qs = model.objects.all()
                if hasattr(model, 'is_active') or 'is_active' in [f.name for f in model._meta.get_fields()]:
                    try:
                        qs = qs.filter(is_active=True)
                    except Exception:
                        pass
                qs = qs.order_by('display_order', 'id') if 'display_order' in [f.name for f in model._meta.get_fields()] else qs.order_by('id')
                return [{'value': str(obj.id), 'label': getattr(obj, 'name', str(obj))} for obj in qs]
            return []
        options = []
        for opt in field.field_options.filter(is_active=True).order_by('display_order', 'id'):
            options.append({'value': opt.value, 'label': opt.label})
        if not options:
            options = [{'value': o.get('value', o.get('label', '')), 'label': o.get('label', '')}
                       for o in field.get_options() if isinstance(o, dict)]
        return options

    def get_field_rules(self, field):
        """HTML5 / client-side validation attributes derived from the config."""
        rules = {
            'name': field.field_name,
            'type': field.field_type,
            'required': field.required,
            'readonly': field.readonly,
            'visible': field.visible,
            'label': field.label,
            'placeholder': field.placeholder,
            'help_text': field.help_text,
            'min_length': field.min_length,
            'max_length': field.max_length,
            'min_value': str(field.min_value) if field.min_value is not None else None,
            'max_value': str(field.max_value) if field.max_value is not None else None,
            'regex_pattern': field.regex_pattern,
            'validator_type': field.validator_type,
            'messages': field.validation_messages or {},
            'conditions': field.conditions or [],
        }
        return rules

    def get_rules_json(self):
        """JSON blob used to keep client-side attributes in sync with config."""
        import json
        return json.dumps([self.get_field_rules(f) for f in self.get_visible_fields()])

    # ------------------------------------------------------------- messages
    def message(self, field, key, fallback):
        return (field.validation_messages or {}).get(key) or fallback

    # ------------------------------------------------------------ validation
    def _clean_value(self, value):
        if value is None:
            return ''
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def validate_value(self, field, raw_value):
        """Validate one field value against its DB configuration.

        Returns a list of error strings (empty == valid).
        """
        errors = []
        value = self._clean_value(raw_value)

        if field.required and not value:
            errors.append(self.message(field, 'required', 'This field is required.'))
            return errors

        if not value:
            return errors  # optional + empty = valid

        if field.field_type in ('number', 'date') or field.validator_type == 'number':
            if field.field_type == 'date':
                from django.core.validators import ValidationError
                from datetime import date
                try:
                    parsed = date.fromisoformat(value)
                    if field.min_value is not None and parsed < date.fromisoformat(str(field.min_value)):
                        errors.append(self.message(field, 'min_value', f'Minimum value is {field.min_value}.'))
                    if field.max_value is not None and parsed > date.fromisoformat(str(field.max_value)):
                        errors.append(self.message(field, 'max_value', f'Maximum value is {field.max_value}.'))
                except ValueError:
                    errors.append(self.message(field, 'invalid', 'Enter a valid date.'))
            else:
                try:
                    num = float(value)
                    if field.min_value is not None and num < float(field.min_value):
                        errors.append(self.message(field, 'min_value', f'Minimum value is {field.min_value}.'))
                    if field.max_value is not None and num > float(field.max_value):
                        errors.append(self.message(field, 'max_value', f'Maximum value is {field.max_value}.'))
                except ValueError:
                    errors.append(self.message(field, 'invalid', 'Enter a valid number.'))
        else:
            if field.min_length is not None and len(value) < field.min_length:
                errors.append(self.message(field, 'min_length', f'Please enter at least {field.min_length} characters.'))
            if field.max_length is not None and len(value) > field.max_length:
                errors.append(self.message(field, 'max_length', f'Maximum {field.max_length} characters allowed.'))

        # Regex pattern (explicit or from validator_type)
        pattern = field.regex_pattern
        if not pattern:
            pattern = self._default_pattern(field)
        if pattern:
            try:
                if not re.search(pattern, value):
                    errors.append(self.message(
                        field, 'pattern',
                        self._default_pattern_message(field, pattern),
                    ))
            except re.error:
                pass

        if field.validator_type == 'email':
            if '@' not in value or '.' not in value:
                errors.append(self.message(field, 'email', 'Enter a valid email address.'))
        elif field.validator_type == 'alphabetic':
            if not re.fullmatch(r'[a-zA-Z\s]+', value):
                errors.append(self.message(field, 'alphabetic', 'Only alphabets and spaces are allowed.'))
        elif field.validator_type == 'alphanumeric':
            if field.field_name == 'nielit_registration_number':
                if not re.fullmatch(r'[a-zA-Z0-9 -]*', value):
                    errors.append(self.message(field, 'alphanumeric', 'Only letters, numbers, spaces, and hyphens (-) are allowed.'))
            elif not re.fullmatch(r'[a-zA-Z0-9\s]+', value):
                errors.append(self.message(field, 'alphanumeric', 'Only letters, numbers and spaces are allowed.'))
        elif field.validator_type == 'percentage':
            try:
                num = float(value)
                if num < 0 or num > 100:
                    errors.append(self.message(field, 'percentage', 'Enter a valid percentage between 0 and 100.'))
            except ValueError:
                errors.append(self.message(field, 'percentage', 'Enter a valid percentage between 0 and 100.'))

        return errors

    def _default_pattern(self, field):
        if field.validator_type == 'phone':
            return r'^[1-9][0-9]{9}$'
        if field.validator_type == 'aadhaar':
            return r'^[1-9][0-9]{11}$'
        if field.validator_type == 'pincode':
            return r'^[0-9]{6}$'
        return ''

    def _default_pattern_message(self, field, pattern):
        if field.validator_type == 'phone':
            return 'Please enter a valid 10-digit mobile number.'
        if field.validator_type == 'aadhaar':
            return 'Please enter a valid 12-digit Aadhaar number.'
        if field.validator_type == 'pincode':
            return 'Please enter a valid 6-digit pincode.'
        return 'Please enter a valid value.'

    def validate_file(self, field, uploaded_file):
        """Validate an uploaded file against the field config.

        Checks extension + MIME type + size (+ image validity where applicable).
        """
        errors = []
        name = getattr(uploaded_file, 'name', '') or ''
        ext = Path(name).suffix.lower().lstrip('.')
        mime_type, _ = mimetypes.guess_type(name)
        size = getattr(uploaded_file, 'size', 0) or 0

        allowed = [t.strip().lower().lstrip('.') for t in (field.allowed_file_types or [])]
        if allowed:
            if ext not in allowed:
                errors.append(self.message(
                    field, 'file_type',
                    f'Only {", ".join(a.upper() for a in allowed)} files are allowed.',
                ))

        if field.max_file_size:
            limit = field.max_file_size * 1024
            if size > limit:
                errors.append(self.message(
                    field, 'max_file_size',
                    f'File exceeds maximum size of {field.max_file_size} KB.',
                ))
        if field.min_file_size:
            limit = field.min_file_size * 1024
            if size and size < limit:
                errors.append(self.message(
                    field, 'min_file_size',
                    f'File must be at least {field.min_file_size} KB.',
                ))

        # Validate the actual content, not just the filename extension.
        if errors:
            return errors
        if 'pdf' in (ext,) or (mime_type and mime_type == 'application/pdf'):
            if uploaded_file and hasattr(uploaded_file, 'read'):
                uploaded_file.seek(0)
                head = uploaded_file.read(5)
                uploaded_file.seek(0)
                if head[:4] != b'%PDF':
                    errors.append(self.message(field, 'invalid_file', 'The file is not a valid PDF.'))
        elif ext in ('jpg', 'jpeg', 'png', 'webp'):
            try:
                from PIL import Image
                uploaded_file.seek(0)
                img = Image.open(uploaded_file)
                img.verify()
                uploaded_file.seek(0)
                if field.image_min_width or field.image_min_height:
                    img2 = Image.open(uploaded_file)
                    w, h = img2.size
                    uploaded_file.seek(0)
                    if field.image_min_width and w < field.image_min_width:
                        errors.append(self.message(field, 'min_width', f'Image width must be at least {field.image_min_width}px.'))
                    if field.image_min_height and h < field.image_min_height:
                        errors.append(self.message(field, 'min_height', f'Image height must be at least {field.image_min_height}px.'))
            except Exception:
                errors.append(self.message(field, 'invalid_file', 'The uploaded file is not a valid image.'))
        return errors

    def validate_submission(self, data, files=None, field_map=None):
        """Validate all active+visible fields against the DB configuration.

        data   -> dict of POST field_name -> value
        files  -> UploadedFile dict (field_name -> file)
        field_map -> optional preloaded {field_name: config} to avoid re-querying

        Returns {field_name: [errors...]} for failed fields only.
        """
        from .models import FormFieldConfiguration
        if field_map is None:
            field_map = {f.field_name: f for f in FormFieldConfiguration.objects.filter(is_active=True)}
        all_errors = {}
        files = files or {}
        for fname, field in field_map.items():
            if not field.visible:
                continue
            if field.field_type == 'file':
                uploaded = files.get(field.field_name)
                # Required file: must be present (already-uploaded files handled by caller).
                if field.required and uploaded is None:
                    all_errors.setdefault(field.field_name, []).append(
                        self.message(field, 'required', f'{field.label} is required.')
                    )
                elif uploaded is not None:
                    file_errors = self.validate_file(field, uploaded)
                    if file_errors:
                        all_errors[field.field_name] = file_errors
                continue
            raw = data.get(field.field_name, '')
            if raw is None:
                raw = ''
            errors = self.validate_value(field, raw)
            if errors:
                all_errors[field.field_name] = errors
        return all_errors

    # --------------------------------------------------------------- preview
    def preview_context(self, extra=None):
        """Context used by the admin live-preview (mirrors the registration view)."""
        context = {}
        sections = []
        for entry in self.get_fields_by_section(active_only=True, visible_only=False):
            for f in entry['fields']:
                f.preview_options = self.get_options(f)
            sections.append({
                'section': entry['section'],
                'fields': entry['fields'],
            })
        context['fb_sections'] = sections
        context['fb_rules_json'] = self.get_rules_json()
        if extra:
            context.update(extra)
        return context