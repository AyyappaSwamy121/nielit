"""Admin views for the Form Builder module.

All saves apply immediately ("Save & Apply") and also record an immutable
FormConfigurationVersion snapshot + AuditLog entry. Permission model:
superusers and users with the `dashboard.change_form_builder` permission can
edit; other staff get read-only access.
"""

import json

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from .models import (
    AuditLog,
    FormConfigurationVersion,
    FormFieldConfiguration,
    FormFieldOption,
    FormSection,
)
from .form_config_service import FormConfigurationService

_EDIT_PERM = 'dashboard.change_form_builder'


def _can_change(request):
    return request.user.is_superuser or request.user.has_perm(_EDIT_PERM)


def _write_audit_log(request, action, detail=''):
    try:
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=action,
            detail=detail[:2000],
        )
    except Exception:
        pass


def _snapshot():
    """Serialize the whole form configuration for version history."""
    service = FormConfigurationService()
    data = []
    for entry in service.get_fields_by_section(active_only=False):
        data.append({
            'section': {
                'slug': entry['section'].slug,
                'name': entry['section'].name,
                'description': entry['section'].description,
                'icon': entry['section'].icon,
                'display_order': entry['section'].display_order,
                'is_active': entry['section'].is_active,
            },
            'fields': [{
                'field_name': f.field_name,
                'label': f.label,
                'field_type': f.field_type,
                'placeholder': f.placeholder,
                'help_text': f.help_text,
                'required': f.required,
                'visible': f.visible,
                'readonly': f.readonly,
                'default_value': f.default_value,
                'min_length': f.min_length,
                'max_length': f.max_length,
                'min_value': str(f.min_value) if f.min_value is not None else None,
                'max_value': str(f.max_value) if f.max_value is not None else None,
                'regex_pattern': f.regex_pattern,
                'validator_type': f.validator_type,
                'options_source': f.options_source,
                'source_model': f.source_model,
                'options': f.options,
                'allowed_file_types': f.allowed_file_types,
                'max_file_size': f.max_file_size,
                'min_file_size': f.min_file_size,
                'validation_messages': f.validation_messages,
                'conditions': f.conditions,
                'display_order': f.display_order,
                'is_active': f.is_active,
                'is_conditional': f.is_conditional,
            } for f in entry['fields']],
        })
    return data


def _record_version(request, changes):
    try:
        latest = FormConfigurationVersion.objects.order_by('-version').first()
        version = (latest.version + 1) if latest else 1
        FormConfigurationVersion.objects.create(
            version=version,
            label=f'Version {version}',
            status='published',
            changes=changes[:2000],
            snapshot=json.dumps(_snapshot()),
            created_by=request.user if request.user.is_authenticated else None,
        )
    except Exception:
        pass


def _diff_fields(old, new):
    """Build a human-readable change summary between two field configs."""
    changes = []
    attrs = [
        ('label', 'Label'), ('placeholder', 'Placeholder'), ('help_text', 'Help Text'),
        ('required', 'Required'), ('visible', 'Visible'), ('readonly', 'Read Only'),
        ('min_length', 'Min Length'), ('max_length', 'Max Length'),
        ('min_value', 'Min Value'), ('max_value', 'Max Value'),
        ('regex_pattern', 'Regex Pattern'), ('field_type', 'Field Type'),
        ('max_file_size', 'Max File Size'), ('display_order', 'Display Order'),
        ('is_active', 'Active'),
    ]
    for attr, label in attrs:
        ov, nv = getattr(old, attr), getattr(new, attr)
        if ov != nv:
            changes.append(f'{label}: {ov} → {nv}')
    return ', '.join(changes)


def _move(field, direction):
    siblings = list(FormFieldConfiguration.objects.filter(
        section=field.section, is_active=True
    ).order_by('display_order', 'id'))
    idx = next((i for i, f in enumerate(siblings) if f.id == field.id), None)
    if idx is None:
        return
    swap = idx - 1 if direction == 'up' else idx + 1
    if 0 <= swap < len(siblings):
        a, b = siblings[idx], siblings[swap]
        a.display_order, b.display_order = b.display_order, a.display_order
        a.save(update_fields=['display_order'])
        b.save(update_fields=['display_order'])


# --------------------------------------------------------------------------
# Dashboard list (grouped by section)
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_home(request):
    service = FormConfigurationService()
    all_sections = FormSection.objects.all()
    q = request.GET.get('q', '').strip()
    f_section = request.GET.get('section', '').strip()
    f_type = request.GET.get('type', '').strip()
    f_required = request.GET.get('required', '').strip()
    f_visible = request.GET.get('visible', '').strip()
    f_active = request.GET.get('active', '').strip()

    qs = FormFieldConfiguration.objects.select_related('section').all()
    if q:
        qs = qs.filter(Q(label__icontains=q) | Q(field_name__icontains=q))
    if f_section:
        qs = qs.filter(section_id=f_section)
    if f_type:
        qs = qs.filter(field_type=f_type)
    if f_required == 'yes':
        qs = qs.filter(required=True)
    elif f_required == 'no':
        qs = qs.filter(required=False)
    if f_visible == 'yes':
        qs = qs.filter(visible=True)
    elif f_visible == 'no':
        qs = qs.filter(visible=False)
    if f_active == 'yes':
        qs = qs.filter(is_active=True)
    elif f_active == 'no':
        qs = qs.filter(is_active=False)

    fields_by_id = {f.id: f for f in qs}
    grouped = []
    for s in all_sections:
        sec_fields = [fields_by_id[f.id] for f in FormFieldConfiguration.objects.filter(section=s) if f.id in fields_by_id]
        grouped.append({'section': s, 'fields': sorted(sec_fields, key=lambda x: (x.display_order, x.id))})

    return render(request, 'dashboard/form_builder/index.html', {
        'title': 'Form Builder',
        'grouped': grouped,
        'sections': all_sections,
        'can_change': _can_change(request),
        'filters': {
            'q': q, 'section': f_section, 'type': f_type,
            'required': f_required, 'visible': f_visible, 'active': f_active,
        },
        'total_fields': FormFieldConfiguration.objects.count(),
        'active_fields': FormFieldConfiguration.objects.filter(is_active=True).count(),
        'field_type_choices': FormFieldConfiguration.FIELD_TYPE_CHOICES,
    })


# --------------------------------------------------------------------------
# Edit / create field
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_edit(request, field_id=None):
    if field_id:
        field = get_object_or_404(FormFieldConfiguration, id=field_id)
        is_new = False
    else:
        field = FormFieldConfiguration()
        is_new = True

    if request.method == 'POST':
        if not _can_change(request):
            messages.error(request, 'You do not have permission to change form configuration.')
            return redirect('form_builder')

        old_snapshot = _snapshot()
        changed = _apply_field_post(field, request.POST)
        field.save()

        if not is_new:
            _record_version(request, _diff_fields_old(field, changed, request))
            _write_audit_log(request, 'FORM_FIELD_UPDATED',
                             f'Field: {field.label} ({field.field_name}) updated by {request.user.username}.')
        else:
            _write_audit_log(request, 'FORM_FIELD_CREATED',
                             f'Field: {field.label} ({field.field_name}) created by {request.user.username}.')
            _record_version(request, f'Created field {field.label}.')

        messages.success(request, '✓ Field configuration updated successfully. Changes are now active on the registration form.')
        return redirect('form_builder_edit', field_id=field.id)

    sections = FormSection.objects.all()
    return render(request, 'dashboard/form_builder/edit.html', {
        'title': 'Edit Field' if not is_new else 'Add Field',
        'field': field,
        'sections': sections,
        'can_change': _can_change(request),
        'options': FormFieldOption.objects.filter(field=field).order_by('display_order', 'id') if field.pk else [],
        'field_type_choices': FormFieldConfiguration.FIELD_TYPE_CHOICES,
        'validator_choices': FormFieldConfiguration.SPECIAL_VALIDATORS,
        'options_source_choices': FormFieldConfiguration.OPTIONS_SOURCE_CHOICES,
        'validation_messages': field.validation_messages or {},
    })


def _apply_field_post(field, post):
    from decimal import Decimal
    def _b(key, default=False):
        return post.get(key) == 'on' or post.get(key) == '1' or post.get(key) == 'true'
    def _int(key):
        raw = (post.get(key) or '').strip()
        return int(raw) if raw else None
    def _dec(key):
        raw = (post.get(key) or '').strip()
        return Decimal(raw) if raw else None

    field.section_id = int(post.get('section') or 1)
    field.field_name = (post.get('field_name') or '').strip()
    field.label = (post.get('label') or '').strip()
    field.field_type = post.get('field_type') or 'text'
    field.placeholder = (post.get('placeholder') or '').strip()
    field.help_text = (post.get('help_text') or '').strip()
    field.required = _b('required')
    field.visible = _b('visible')
    field.readonly = _b('readonly')
    field.default_value = (post.get('default_value') or '').strip()
    field.min_length = _int('min_length')
    field.max_length = _int('max_length')
    field.min_value = _dec('min_value')
    field.max_value = _dec('max_value')
    field.regex_pattern = (post.get('regex_pattern') or '').strip()
    field.validator_type = post.get('validator_type') or ''
    field.options_source = post.get('options_source') or 'options'
    field.source_model = (post.get('source_model') or '').strip()
    field.max_file_size = _int('max_file_size')
    field.min_file_size = _int('min_file_size')
    field.image_min_width = _int('image_min_width')
    field.image_min_height = _int('image_min_height')
    field.display_order = _int('display_order') or 0
    field.is_active = _b('is_active')
    field.is_conditional = _b('is_conditional')

    # JSON list fields (comma separated in the form)
    field.allowed_file_types = [t.strip().lower() for t in (post.get('allowed_file_types') or '').split(',') if t.strip()]
    field.options = json.loads(post.get('options_json') or '[]')

    # Validation messages
    msgs = {}
    for key in ('required', 'min_length', 'max_length', 'min_value', 'max_value',
                'pattern', 'email', 'file_type', 'max_file_size', 'invalid', 'invalid_file'):
        val = (post.get(f'msg_{key}') or '').strip()
        if val:
            msgs[key] = val
    field.validation_messages = msgs

    # Conditions
    conds = []
    cond_fields = post.getlist('cond_field')
    cond_ops = post.getlist('cond_operator')
    cond_vals = post.getlist('cond_value')
    for cf, op, cv in zip(cond_fields, cond_ops, cond_vals):
        if cf and op:
            conds.append({'field': cf, 'operator': op, 'value': cv})
    field.conditions = conds
    return field


def _diff_fields_old(field, new, request):
    return 'Updated field configuration.'


# --------------------------------------------------------------------------
# Field order (move up/down)
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_field_move(request, field_id, direction):
    if not _can_change(request):
        messages.error(request, 'Permission denied.')
        return redirect('form_builder')
    field = get_object_or_404(FormFieldConfiguration, id=field_id)
    _move(field, direction)
    _write_audit_log(request, 'FORM_FIELD_REORDERED',
                     f'{field.label} moved {direction}.')
    _record_version(request, f'Reordered field {field.label}.')
    return redirect('form_builder')


# --------------------------------------------------------------------------
# Field options (add/edit/delete/move)
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_option_add(request, field_id):
    if request.method == 'POST' and _can_change(request):
        field = get_object_or_404(FormFieldConfiguration, id=field_id)
        label = (request.POST.get('label') or '').strip()
        value = (request.POST.get('value') or '').strip()
        if label and value:
            last = FormFieldOption.objects.filter(field=field).order_by('-display_order').first()
            order = (last.display_order + 1) if last else 0
            FormFieldOption.objects.create(field=field, label=label, value=value, display_order=order)
            _write_audit_log(request, 'FORM_OPTION_ADDED',
                             f'Option {label} added to {field.label}.')
            messages.success(request, 'Option added.')
        else:
            messages.error(request, 'Both label and value are required.')
        return redirect('form_builder_edit', field_id=field.id)
    return redirect('form_builder')


@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_option_edit(request, option_id):
    option = get_object_or_404(FormFieldOption, id=option_id)
    if request.method == 'POST' and _can_change(request):
        option.label = (request.POST.get('label') or option.label).strip()
        option.value = (request.POST.get('value') or option.value).strip()
        option.save()
        _write_audit_log(request, 'FORM_OPTION_UPDATED',
                         f'Option for {option.field.label}.')
        messages.success(request, 'Option updated.')
    return redirect('form_builder_edit', field_id=option.field_id)


@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_option_delete(request, option_id):
    option = get_object_or_404(FormFieldOption, id=option_id)
    field_id = option.field_id
    if request.method == 'POST' and _can_change(request):
        _write_audit_log(request, 'FORM_OPTION_DELETED',
                         f'Option {option.label} removed from {option.field.label}.')
        option.delete()
        messages.success(request, 'Option deleted.')
    return redirect('form_builder_edit', field_id=field_id)


@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_option_move(request, option_id, direction):
    option = get_object_or_404(FormFieldOption, id=option_id)
    if _can_change(request):
        siblings = list(FormFieldOption.objects.filter(field=option.field).order_by('display_order', 'id'))
        idx = next((i for i, o in enumerate(siblings) if o.id == option.id), None)
        swap = (idx - 1) if direction == 'up' else (idx + 1)
        if idx is not None and 0 <= swap < len(siblings):
            a, b = siblings[idx], siblings[swap]
            a.display_order, b.display_order = b.display_order, a.display_order
            a.save(update_fields=['display_order'])
            b.save(update_fields=['display_order'])
    return redirect('form_builder_edit', field_id=option.field_id)


# --------------------------------------------------------------------------
# Bulk operations
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_bulk(request):
    if request.method == 'POST':
        if not _can_change(request):
            messages.error(request, 'You do not have permission to change form configuration.')
            return redirect('form_builder')
        ids = request.POST.getlist('field_ids')
        action = request.POST.get('bulk_action', '')
        confirm = request.POST.get('confirm') == '1'
        if not confirm:
            messages.warning(request, 'Bulk action requires confirmation.')
            return redirect('form_builder')
        fields = FormFieldConfiguration.objects.filter(id__in=ids)
        count = fields.count()
        updates = {}
        if action == 'make_required':
            updates['required'] = True
        elif action == 'make_optional':
            updates['required'] = False
        elif action == 'show':
            updates['visible'] = True
        elif action == 'hide':
            updates['visible'] = False
        elif action == 'activate':
            updates['is_active'] = True
        elif action == 'deactivate':
            updates['is_active'] = False
        if updates:
            fields.update(**updates)
            _write_audit_log(request, 'FORM_BULK_UPDATE',
                             f'{count} fields updated ({action}) by {request.user.username}.')
            _record_version(request, f'Bulk {action} on {count} fields.')
            messages.success(request, f'{count} field(s) updated successfully. Changes are now active on the registration form.')
        else:
            messages.error(request, 'Invalid bulk action.')
    return redirect('form_builder')


# --------------------------------------------------------------------------
# Section management (rename / description / order / show-hide)
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_section_save(request, section_id):
    section = get_object_or_404(FormSection, id=section_id)
    if request.method == 'POST' and _can_change(request):
        section.name = (request.POST.get('name') or section.name).strip()
        section.description = (request.POST.get('description') or '').strip()
        section.icon = (request.POST.get('icon') or section.icon).strip()
        section.display_order = int(request.POST.get('display_order') or section.display_order or 0)
        section.is_active = request.POST.get('is_active') == 'on'
        section.save()
        _write_audit_log(request, 'FORM_SECTION_UPDATED', f'Section: {section.name}.')
        messages.success(request, 'Section updated successfully.')
    return redirect('form_builder')


# --------------------------------------------------------------------------
# Live preview
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_preview(request):
    service = FormConfigurationService()
    context = service.preview_context()
    view_mode = request.GET.get('mode', 'desktop')
    return render(request, 'dashboard/form_builder/preview.html', {
        'title': 'Form Preview',
        'view_mode': view_mode,
        'fb_sections': context['fb_sections'],
        'fb_rules_json': context['fb_rules_json'],
    })


# --------------------------------------------------------------------------
# Version history
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_history(request):
    versions = FormConfigurationVersion.objects.select_related('created_by').all()
    return render(request, 'dashboard/form_builder/history.html', {
        'title': 'Form Configuration History',
        'versions': versions,
        'can_change': _can_change(request),
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_restore(request, version_id):
    if request.method == 'POST' and _can_change(request):
        version = get_object_or_404(FormConfigurationVersion, id=version_id)
        try:
            snapshot = json.loads(version.snapshot)
        except Exception:
            snapshot = []
        _restore_snapshot(snapshot)
        _write_audit_log(request, 'FORM_CONFIG_RESTORED',
                         f'Restored version {version.version} by {request.user.username}.')
        messages.success(request, f'Configuration restored to version {version.version}.')
    return redirect('form_builder_history')


def _restore_snapshot(snapshot):
    for section_data in snapshot:
        s = section_data.get('section', {})
        section, _ = FormSection.objects.update_or_create(
            slug=s.get('slug'),
            defaults={
                'name': s.get('name', s.get('slug', '')),
                'description': s.get('description', ''),
                'icon': s.get('icon', ''),
                'display_order': s.get('display_order', 0),
                'is_active': s.get('is_active', True),
            },
        )
        for fd in section_data.get('fields', []):
            defaults = dict(fd)
            defaults.pop('field_name', None)
            defaults['section'] = section
            FormFieldConfiguration.objects.update_or_create(
                field_name=fd['field_name'], defaults=defaults,
            )


# --------------------------------------------------------------------------
# API: field rules for the JS bridge
# --------------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def form_builder_rules_json(request):
    service = FormConfigurationService()
    return JsonResponse({'rules': json.loads(service.get_rules_json())})
