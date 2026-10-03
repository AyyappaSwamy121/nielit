"""Single source of truth for every number shown on the CSC Admin Portal dashboard.

Every value here is calculated live from the source tables (StudentApplication,
UploadedDocument, master data, AuditLog, ExportJob, ...). No dashboard-specific
count tables are used and nothing is hard-coded.
"""

import os
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from registrations.models import StudentApplication, UploadedDocument, SUBMITTED_STATUS_CODES
from masterdata.models import District, Program, State

# The dashboard understands exactly two application buckets: Draft (INCOMPLETE)
# and Submitted (every officially-submitted status in the model). The canonical
# submitted bucket comes straight from registrations.SUBMITTED_STATUS_CODES -
# it includes the current SUBMITTED code plus the legacy codes
# (PENDING/APPROVED/REJECTED/CORRECTION) that pre-existing records already use,
# so existing data is read correctly with no migration. Bucket membership is
# determined ONLY by the application.status ForeignKey - never by
# submission_date or by whether other fields are populated.
DRAFT_CODE = 'INCOMPLETE'
SUBMITTED_CODE = 'SUBMITTED'
DASHBOARD_STATUS_CODES = (DRAFT_CODE,) + tuple(SUBMITTED_STATUS_CODES)

# Mandatory document types (lower-cased) - mirrors the final-submission check in
# registrations/views.py so the dashboard and the workflow always agree.
MANDATORY_DOC_TYPES = [
    'passport_photo',
    'signature',
    'aadhaar',
    'left_thumb',
    'father_signature',
    'community_certificate',
    'additional_documents',
]

DOC_TYPE_LABELS = {
    'passport_photo': 'Passport Photo',
    'signature': 'Signature',
    'aadhaar': 'Aadhaar Card',
    'left_thumb': 'Thumb Impression',
    'father_signature': "Father's Signature",
    'community_certificate': 'Community Certificate',
    'additional_documents': 'Additional Documents',
    'abc_id': 'ABC ID',
    'registration_screenshot': 'Registration Screenshot',
}

ACTIVITY_LABELS = {
    'BULK_CHANGE_STATUS': 'Application status changed',
    'BULK_ASSIGN_PARTNER': 'Training partner assigned',
    'BULK_ASSIGN_BATCH': 'Batch code assigned',
    'BULK_NOTIFY': 'Bulk email sent',
    'BULK_CORRECTION': 'Correction requested',
    'BULK_VERIFY': 'Applications verified',
    'EXPORT_CENTER': 'Export generated',
    'EXPORT_FAILED': 'Export failed',
    'SETTINGS_CHANGED': 'Platform settings updated',
    'BACKUP_CREATED': 'Backup created',
    'BACKUP_FAILED': 'Backup failed',
    'BACKUP_DOWNLOADED': 'Backup downloaded',
    'BACKUP_UPLOADED': 'Backup uploaded',
    'RESTORE_STARTED': 'Restore started',
    'RESTORE_COMPLETED': 'System restored',
    'RESTORE_FAILED': 'Restore failed',
}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _distribution(qs, field):
    """Return [(label, count)] grouped by a values/annotate field, read-only."""
    rows = (
        qs.values(field)
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    out = []
    for r in rows:
        label = r[field]
        if label in (None, '', 'None'):
            label = 'Not specified'
        out.append((label, r['count']))
    return out


def _bucketed(items, limit=5):
    """Reduce [(label, count)] to the top `limit` rows plus a single 'Other' row."""
    items = sorted(items, key=lambda x: x[1], reverse=True)
    out = [{'label': label, 'count': count} for label, count in items[:limit]]
    rest = sum(count for _, count in items[limit:])
    if rest:
        out.append({'label': 'Other', 'count': rest})
    return out


def _distribution_with_ids(qs, id_field, name_field):
    """Return [{'label', 'count', 'id'}] grouped by a FK, preserving the FK id."""
    rows = (
        qs.values(id_field, name_field)
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    out = []
    for r in rows:
        label = r[name_field] or 'Not specified'
        out.append({'label': label, 'count': r['count'], 'id': r[id_field]})
    return out


def _bucketed_with_ids(items, limit=5):
    """Reduce [{'label','count','id'}] to the top `limit` plus one 'Other' row."""
    items = sorted(items, key=lambda x: x['count'], reverse=True)
    out = list(items[:limit])
    rest = sum(x['count'] for x in items[limit:])
    if rest:
        out.append({'label': 'Other', 'count': rest, 'id': None})
    return out


def _ids_for_quality(condition):
    """
    Returns application PKs matching a data-quality condition. Used both by the
    dashboard alert cards and by the Applications page drill-down filter.
    """
    required = MANDATORY_DOC_TYPES
    qs = StudentApplication.objects.filter(status__code__in=SUBMITTED_STATUS_CODES)

    if condition == 'missing_docs':
        ids = []
        apps = qs.prefetch_related('documents')
        for app in apps:
            present = {d.doc_type.lower() for d in app.documents.all()}
            if any(r not in present for r in required):
                ids.append(app.pk)
        return ids

    if condition == 'invalid_email':
        return list(
            qs.filter(Q(email__isnull=True) | Q(email='') | ~Q(email__contains='@'))
            .values_list('pk', flat=True)
        )

    if condition == 'incomplete_education':
        return list(
            qs.filter(Q(qualification__isnull=True) | Q(year_of_passing__isnull=True))
            .values_list('pk', flat=True)
        )

    if condition == 'dup_mobile':
        dupe_values = (
            qs.exclude(mobile_number__isnull=True)
            .exclude(mobile_number='')
            .values('mobile_number')
            .annotate(c=Count('id'))
            .filter(c__gt=1)
            .values_list('mobile_number', flat=True)
        )
        return list(qs.filter(mobile_number__in=dupe_values).values_list('pk', flat=True))

    if condition == 'dup_aadhaar':
        dupe_values = (
            qs.exclude(aadhaar_number__isnull=True)
            .exclude(aadhaar_number='')
            .values('aadhaar_number')
            .annotate(c=Count('id'))
            .filter(c__gt=1)
            .values_list('aadhaar_number', flat=True)
        )
        return list(qs.filter(aadhaar_number__in=dupe_values).values_list('pk', flat=True))

    if condition == 'dup_email':
        dupe_values = (
            qs.exclude(email__isnull=True)
            .exclude(email='')
            .values('email')
            .annotate(c=Count('id'))
            .filter(c__gt=1)
            .values_list('email', flat=True)
        )
        return list(qs.filter(email__in=dupe_values).values_list('pk', flat=True))

    return []


def duplicate_stats():
    """Counts of submitted applications sharing mobile / aadhaar / email."""
    qs = StudentApplication.objects.filter(status__code__in=SUBMITTED_STATUS_CODES)

    def count(field):
        dupe_values = (
            qs.exclude(**{f'{field}__isnull': True})
            .exclude(**{f'{field}': ''})
            .values(field)
            .annotate(c=Count('id'))
            .filter(c__gt=1)
            .values_list(field, flat=True)
        )
        return qs.filter(**{f'{field}__in': list(dupe_values)}).count()

    return [
        {'label': 'Aadhaar', 'count': count('aadhaar_number'), 'quality': 'dup_aadhaar'},
        {'label': 'Mobile', 'count': count('mobile_number'), 'quality': 'dup_mobile'},
        {'label': 'Email', 'count': count('email'), 'quality': 'dup_email'},
    ]


# ---------------------------------------------------------------------------
# Trend (Application Trend chart)
# ---------------------------------------------------------------------------

def _trend_data(request, qs):
    """Daily/weekly submission counts for the requested trend range."""
    today = timezone.localdate()
    trend_param = request.GET.get('trend', '30')
    trend_from = request.GET.get('trend_from', '')
    trend_to = request.GET.get('trend_to', '')

    if trend_param == '7':
        start = today - timedelta(days=6)
        end = today
        granularity = 'day'
    elif trend_param == '90':
        start = today - timedelta(days=89)
        end = today
        granularity = 'week'
    elif trend_param == 'custom':
        try:
            start = timezone.datetime.strptime(trend_from, '%Y-%m-%d').date() if trend_from else today - timedelta(days=29)
        except ValueError:
            start = today - timedelta(days=29)
        try:
            end = timezone.datetime.strptime(trend_to, '%Y-%m-%d').date() if trend_to else today
        except ValueError:
            end = today
        if end < start:
            start, end = end, start
        granularity = 'day'
    else:  # '30'
        start = today - timedelta(days=29)
        end = today
        granularity = 'day'

    daily = dict(
        qs.filter(submission_date__date__gte=start, submission_date__date__lte=end)
        .annotate(day=TruncDate('submission_date'))
        .values('day')
        .annotate(c=Count('id'))
        .values_list('day', 'c')
    )

    if granularity == 'day':
        labels, counts = [], []
        cursor = start
        while cursor <= end:
            labels.append(cursor.strftime('%a, %b %d'))
            counts.append(daily.get(cursor, 0))
            cursor += timedelta(days=1)
    else:
        # Weekly buckets keyed by the week's Monday.
        weekly = {}
        cursor = start
        while cursor <= end:
            week_start = cursor - timedelta(days=cursor.weekday())
            weekly.setdefault(week_start, 0)
            weekly[week_start] += daily.get(cursor, 0)
            cursor += timedelta(days=1)
        labels = [k.strftime('%b %d') for k in sorted(weekly)]
        counts = [weekly[k] for k in sorted(weekly)]

    return {
        'range': trend_param,
        'from_date': start.isoformat(),
        'to_date': end.isoformat(),
        'labels': labels,
        'counts': counts,
    }


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------

def system_health():
    """Live checks against real services. Never reports Healthy blindly."""
    checks = []

    # Database
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks.append({'name': 'Database', 'icon': 'storage', 'status': 'ok', 'detail': 'Connected'})
    except Exception as exc:
        checks.append({'name': 'Database', 'icon': 'storage', 'status': 'error', 'detail': str(exc)[:120]})

    # File storage (media root)
    try:
        media_root = str(settings.MEDIA_ROOT)
        writable = os.path.isdir(media_root) and os.access(media_root, os.W_OK)
        checks.append({
            'name': 'File Storage',
            'icon': 'folder_open',
            'status': 'ok' if writable else 'error',
            'detail': 'Writable' if writable else 'Not writable',
        })
    except Exception as exc:
        checks.append({'name': 'File Storage', 'icon': 'folder_open', 'status': 'error', 'detail': str(exc)[:120]})

    # Document storage: probe the actual upload directory used for documents.
    try:
        doc_folder = os.path.join(str(settings.MEDIA_ROOT), 'documents')
        probe = doc_folder if os.path.isdir(doc_folder) else str(settings.MEDIA_ROOT)
        writable = os.path.isdir(probe) and os.access(probe, os.W_OK)
        checks.append({
            'name': 'Document Storage',
            'icon': 'folder_zip',
            'status': 'ok' if writable else 'error',
            'detail': 'Writable' if writable else 'Not writable',
        })
    except Exception as exc:
        checks.append({'name': 'Document Storage', 'icon': 'folder_zip', 'status': 'error', 'detail': str(exc)[:120]})

    # Email service: only report Healthy after a real SMTP ping when configured.
    try:
        from django.core import mail
        host = getattr(settings, 'EMAIL_HOST', '') or ''
        if not host:
            checks.append({'name': 'Email Service', 'icon': 'mail', 'status': 'warn', 'detail': 'Not configured'})
        else:
            try:
                ok = bool(mail.get_connection().ping())
                checks.append({
                    'name': 'Email Service',
                    'icon': 'mail',
                    'status': 'ok' if ok else 'error',
                    'detail': 'Reachable' if ok else 'Unreachable',
                })
            except Exception:
                checks.append({'name': 'Email Service', 'icon': 'mail', 'status': 'error', 'detail': 'Unreachable'})
    except Exception:
        checks.append({'name': 'Email Service', 'icon': 'mail', 'status': 'error', 'detail': 'Check failed'})

    # Auto-save
    try:
        from dashboard.models import PlatformSetting
        interval = PlatformSetting.get_active().auto_save_interval
        try:
            interval = int(interval)
        except (TypeError, ValueError):
            interval = 0
        if interval > 0:
            checks.append({'name': 'Auto-save', 'icon': 'save', 'status': 'ok', 'detail': f'Active ({interval}s)'})
        else:
            checks.append({'name': 'Auto-save', 'icon': 'save', 'status': 'warn', 'detail': 'Disabled'})
    except Exception:
        checks.append({'name': 'Auto-save', 'icon': 'save', 'status': 'warn', 'detail': 'Unknown'})

    return checks


# ---------------------------------------------------------------------------
# Activity feed
# ---------------------------------------------------------------------------

def recent_activity(limit=12):
    """Merged timeline of AuditLog events + application submissions/updates today."""
    from dashboard.models import AuditLog
    today = timezone.localdate()

    items = []

    for log in AuditLog.objects.select_related('user').filter(created_at__date=today)[:40]:
        items.append({
            'time': log.created_at,
            'title': ACTIVITY_LABELS.get(log.action, log.action.replace('_', ' ').title()),
            'detail': log.detail,
            'icon': 'history',
        })

    for app in (
        StudentApplication.objects.filter(submission_date__date=today)
        .filter(status__code__in=SUBMITTED_STATUS_CODES)
        .order_by('-submission_date')
    ):
        items.append({
            'time': app.submission_date,
            'title': f'New application submitted — {app.application_number}',
            'detail': app.full_name or '',
            'icon': 'assignment_turned_in',
        })

    for app in (
        StudentApplication.objects.exclude(status__code='INCOMPLETE')
        .filter(last_updated__date=today)
        .exclude(submission_date__date=today)
        .order_by('-last_updated')
    ):
        items.append({
            'time': app.last_updated,
            'title': f'Application updated — {app.application_number}',
            'detail': app.full_name or '',
            'icon': 'edit_note',
        })

    items.sort(key=lambda x: x['time'] or timezone.now(), reverse=True)
    return items[:limit]


# ---------------------------------------------------------------------------
# Master entry point
# ---------------------------------------------------------------------------

def get_dashboard_data(request):
    today = timezone.localdate()
    now = timezone.now()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    since_24h = now - timedelta(hours=24)

    # Two buckets only. "Submitted" = every officially-submitted status
    # (including legacy PENDING/APPROVED/REJECTED/CORRECTION records so existing
    # data is never hidden), "Draft" = INCOMPLETE. Bucket = status FK only.
    all_apps = StudentApplication.objects.filter(status__code__in=DASHBOARD_STATUS_CODES)
    submitted_apps = all_apps.filter(status__code__in=SUBMITTED_STATUS_CODES)
    draft_apps = all_apps.filter(status__code=DRAFT_CODE)

    # ---- Top-level KPIs ----
    metrics = {
        'total_apps': all_apps.count(),
        'submitted_apps': submitted_apps.count(),
        'draft_apps': draft_apps.count(),
        'submitted_today': submitted_apps.filter(submission_date__date=today).count(),
        'this_week': submitted_apps.filter(submission_date__date__gte=week_start).count(),
        'this_month': submitted_apps.filter(submission_date__date__gte=month_start).count(),
        'last_24h': submitted_apps.filter(submission_date__gte=since_24h).count(),
        'total_states': State.objects.count(),
        'total_districts': District.objects.count(),
        'total_programs': Program.objects.count(),
        'total_institutions': submitted_apps.values('institution').distinct().count(),
        'total_docs': UploadedDocument.objects.count(),
    }

    # ---- Application Lifecycle (only Draft and Submitted) ----
    lifecycle = [
        {'label': 'Submitted', 'value': metrics['submitted_apps'], 'color': '#0d6efd'},
        {'label': 'Draft', 'value': metrics['draft_apps'], 'color': '#6c757d'},
    ]
    lifecycle_total = all_apps.count() or 1
    for item in lifecycle:
        item['pct'] = round(item['value'] / lifecycle_total * 100, 1)

    # ---- Application Trend ----
    trend = _trend_data(request, all_apps)

    # ---- Demographics ----
    gender_dist = _bucketed(_distribution(submitted_apps, 'gender'), limit=3)
    category_dist = _bucketed(_distribution(submitted_apps, 'community__name'), limit=4)
    religion_dist = _bucketed(_distribution(submitted_apps, 'religion__name'), limit=4)

    # ---- Geographic ----
    state_dist = _bucketed(_distribution(submitted_apps, 'state__name'), limit=5)
    district_dist = _bucketed(_distribution(submitted_apps, 'district__name'), limit=5)

    # ---- Programs / Qualifications (carry FK ids so rows can deep-link) ----
    program_dist = _bucketed_with_ids(
        _distribution_with_ids(submitted_apps, 'program_opting_id', 'program_opting__name'),
        limit=5,
    )
    qualification_dist = _bucketed_with_ids(
        _distribution_with_ids(submitted_apps, 'qualification_id', 'qualification__name'),
        limit=5,
    )

    # ---- Training Partners (carry FK id so rows can deep-link) ----
    partner_items = _distribution_with_ids(submitted_apps, 'training_partner_id', 'training_partner__name')
    unassigned = submitted_apps.filter(training_partner__isnull=True).count()
    if unassigned:
        partner_items = [x for x in partner_items if x['label'] != 'Not specified']
        partner_items.append({'label': 'Unassigned', 'count': unassigned, 'id': None})
    partner_dist = _bucketed_with_ids(partner_items, limit=5)

    batch_items = _distribution(submitted_apps, 'batch_code')
    batch_unassigned = submitted_apps.filter(Q(batch_code__isnull=True) | Q(batch_code='')).count()
    if batch_unassigned:
        batch_items = [x for x in batch_items if x[0] != 'Not specified']
        batch_items.append(('Unassigned', batch_unassigned))
    batch_dist = _bucketed(batch_items, limit=5)

    # ---- Recently submitted applications (table) ----
    recent_submitted = (
        submitted_apps
        .select_related('program_opting', 'state', 'district')
        .order_by('-submission_date')[:5]
    )
    total_submitted = metrics['submitted_apps']

    # ---- Document Status ----
    doc_complete = 0
    doc_missing = 0
    missing_per_doc = {key: 0 for key in MANDATORY_DOC_TYPES}
    for app in submitted_apps.prefetch_related('documents'):
        present = {d.doc_type.lower() for d in app.documents.all()}
        absent = [r for r in MANDATORY_DOC_TYPES if r not in present]
        if absent:
            doc_missing += 1
            for key in absent:
                missing_per_doc[key] += 1
        else:
            doc_complete += 1

    most_missing = sorted(
        ({'label': DOC_TYPE_LABELS.get(k, k.replace('_', ' ').title()), 'count': v} for k, v in missing_per_doc.items() if v),
        key=lambda x: x['count'],
        reverse=True,
    )[:5]

    # ---- Data Quality alerts ----
    def alert(label, condition, icon, severity='warning'):
        count = len(_ids_for_quality(condition))
        return {
            'label': label,
            'count': count,
            'icon': icon,
            'severity': severity,
            'quality': condition,
        }

    quality_alerts = [
        alert(f"applications have missing documents", 'missing_docs', 'description'),
        alert(f"applications have invalid email addresses", 'invalid_email', 'mail'),
        alert(f"applications have incomplete education data", 'incomplete_education', 'school'),
        alert(f"applications have duplicate mobile numbers", 'dup_mobile', 'call'),
    ]

    # ---- Duplicate detection ----
    duplicates = duplicate_stats()

    # ---- Export activity ----
    from dashboard.models import ExportJob
    recent_exports = ExportJob.objects.select_related('requested_by')[:5]
    export_total = ExportJob.objects.count()

    # ---- Recent activity ----
    activity = recent_activity()

    # ---- System health ----
    health = system_health()

    return {
        'metrics': metrics,
        'lifecycle': lifecycle,
        'trend': trend,
        'gender_dist': gender_dist,
        'category_dist': category_dist,
        'religion_dist': religion_dist,
        'state_dist': state_dist,
        'district_dist': district_dist,
        'program_dist': program_dist,
        'qualification_dist': qualification_dist,
        'partner_dist': partner_dist,
        'batch_dist': batch_dist,
        'recent_submitted': recent_submitted,
        'total_submitted': total_submitted,
        'doc_complete': doc_complete,
        'doc_missing': doc_missing,
        'doc_pending_upload': metrics['draft_apps'],
        'most_missing': most_missing,
        'quality_alerts': quality_alerts,
        'duplicates': duplicates,
        'recent_exports': recent_exports,
        'export_total': export_total,
        'activity': activity,
        'health': health,
        'chart': {
            'gender': {'labels': [x['label'] for x in gender_dist], 'counts': [x['count'] for x in gender_dist]},
            'category': {'labels': [x['label'] for x in category_dist], 'counts': [x['count'] for x in category_dist]},
            'religion': {'labels': [x['label'] for x in religion_dist], 'counts': [x['count'] for x in religion_dist]},
            'state': {'labels': [x['label'] for x in state_dist], 'counts': [x['count'] for x in state_dist]},
            'district': {'labels': [x['label'] for x in district_dist], 'counts': [x['count'] for x in district_dist]},
            'program': {'labels': [x['label'] for x in program_dist], 'counts': [x['count'] for x in program_dist]},
            'qualification': {'labels': [x['label'] for x in qualification_dist], 'counts': [x['count'] for x in qualification_dist]},
            'partner': {'labels': [x['label'] for x in partner_dist], 'counts': [x['count'] for x in partner_dist]},
            'batch': {'labels': [x['label'] for x in batch_dist], 'counts': [x['count'] for x in batch_dist]},
            'lifecycle': {'labels': [x['label'] for x in lifecycle], 'counts': [x['value'] for x in lifecycle]},
        },
    }