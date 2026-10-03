from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from .models import StudentApplication, UploadedDocument
from masterdata.models import (
    ApplicationStatus, VerificationStatus, TrainingPartner, BatchCode,
    Religion, MaritalStatus, Community, ExServiceStatus, Occupation,
    Qualification, Program, State, District,
)

class UploadedDocumentInline(admin.TabularInline):
    model = UploadedDocument
    extra = 0
    can_delete = False
    
    readonly_fields = [
        'doc_type', 'processing_policy', 'original_file_link', 'compressed_file_link', 'uploaded_at', 
        'document_preview', 'original_size_kb_display', 'optimized_size_kb_display', 
        'width_display', 'height_display', 'dpi_display', 'mime_type_display', 'jpeg_quality_display', 'validation_status_display'
    ]
    
    exclude = [
        'original_file', 'compressed_file', 'original_file_size', 'optimized_file_size', 
        'image_width', 'image_height', 'mime_type', 'compression_percentage', 'jpeg_quality', 'validation_status'
    ]

    def original_file_link(self, obj):
        if obj.original_file:
            import os
            fname = os.path.basename(obj.original_file.name)
            return format_html('<a href="{}" title="{}" target="_blank" rel="noopener">{}</a>', obj.original_file.url, fname, fname)
        return "-"
    original_file_link.short_description = "Original File"

    def compressed_file_link(self, obj):
        if obj.compressed_file:
            import os
            fname = os.path.basename(obj.compressed_file.name)
            return format_html('<a href="{}" title="{}" target="_blank" rel="noopener">{}</a>', obj.compressed_file.url, fname, fname)
        return "-"
    compressed_file_link.short_description = "Compressed File"

    def original_size_kb_display(self, obj):
        if obj.original_size_kb:
            return f"{obj.original_size_kb} KB"
        return "-"
    original_size_kb_display.short_description = "Original Size"

    def optimized_size_kb_display(self, obj):
        if obj.optimized_size_kb:
            return f"{obj.optimized_size_kb} KB"
        return "-"
    optimized_size_kb_display.short_description = "Optimized Size"

    def width_display(self, obj):
        if obj.mime_type == 'application/pdf' or obj.doc_type in ['abc_screenshot', 'aadhaar_pdf', 'community_certificate', 'registration_screenshot', 'supporting_documents']:
            return "-"
        return f"{obj.image_width} px" if obj.image_width else "-"
    width_display.short_description = "Width"

    def height_display(self, obj):
        if obj.mime_type == 'application/pdf' or obj.doc_type in ['abc_screenshot', 'aadhaar_pdf', 'community_certificate', 'registration_screenshot', 'supporting_documents']:
            return "-"
        return f"{obj.image_height} px" if obj.image_height else "-"
    height_display.short_description = "Height"

    def dpi_display(self, obj):
        if obj.mime_type == 'application/pdf' or obj.doc_type in ['abc_screenshot', 'aadhaar_pdf', 'community_certificate', 'registration_screenshot', 'supporting_documents']:
            return "-"
        dpi_val = obj.actual_dpi
        if dpi_val:
            return f"{dpi_val} DPI"
        return "-"
    dpi_display.short_description = "DPI"

    def mime_type_display(self, obj):
        if obj.mime_type:
            return obj.mime_type
        return "-"
    mime_type_display.short_description = "MIME Type"
    
    def document_preview(self, obj):
        file_field = obj.compressed_file if obj.compressed_file else obj.original_file
        if not file_field:
            return "-"
            
        url = file_field.url.lower()
        if url.endswith('.pdf'):
            return format_html('<a href="{}" target="_blank" rel="noopener" class="button" style="background:#dc3545; color:white; padding:5px 10px; border-radius:4px; text-decoration:none; white-space:nowrap;">View PDF</a>', file_field.url)
        elif url.endswith(('.png', '.jpg', '.jpeg')):
            label = "Image"
            if "passport" in obj.doc_type.lower(): label = "Photo"
            elif "signature" in obj.doc_type.lower(): label = "Signature"
            elif "thumb" in obj.doc_type.lower(): label = "Thumb"
            return format_html('<a href="{}" target="_blank" rel="noopener" title="{}"><img src="{}" style="max-height: 40px; border-radius: 4px; border:1px solid #ddd;"/></a>', file_field.url, label, file_field.url)
        return "-"
    document_preview.short_description = 'Preview'

    def jpeg_quality_display(self, obj):
        if obj.jpeg_quality:
            return f"Quality {obj.jpeg_quality}"
        return "-"
    jpeg_quality_display.short_description = "JPEG Quality"

    def validation_status_display(self, obj):
        if obj.validation_status == 'PASS':
            return format_html('<span style="color: green; font-weight: bold;">&#10003; PASS</span>')
        elif obj.validation_status == 'FAIL':
            return format_html('<span style="color: red; font-weight: bold;">&#10007; FAIL</span>')
        return "-"
    validation_status_display.short_description = "Validation"


# ---------------------------------------------------------------------------
# GROUPED LIST FILTERS
# Each filter renders as a <select> inside the right-hand sticky filter panel.
# `group` controls the section heading shown in that panel; parameter_name
# drives the GET query param so the changelist filters the existing records.
# Status filters reuse the existing ApplicationStatus/VerificationStatus rows.
# ---------------------------------------------------------------------------

class GroupedFKFilter(SimpleListFilter):
    """Base filter for a ForeignKey field, rendered in a menu group."""
    group = ''
    fk_model = None
    fk_field = None

    def lookups(self, request, model_admin):
        return [(obj.pk, str(obj)) for obj in self.fk_model.objects.order_by('name')]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{f'{self.fk_field}_id': self.value()})
        return queryset


class ApplicationStatusFilter(GroupedFKFilter):
    title = 'Application Status'
    parameter_name = 'status'
    group = 'Application'
    fk_model = ApplicationStatus
    fk_field = 'status'


class VerificationStatusFilter(GroupedFKFilter):
    title = 'Verification Status'
    parameter_name = 'verification_status'
    group = 'Application'
    fk_model = VerificationStatus
    fk_field = 'verification_status'


class ArchiveFilter(SimpleListFilter):
    title = 'Archived'
    parameter_name = 'is_archived'
    group = 'Application'

    def lookups(self, request, model_admin):
        return [('True', 'Yes'), ('False', 'No')]

    def queryset(self, request, queryset):
        if self.value() in ('True', '1'):
            return queryset.filter(is_archived=True)
        if self.value() in ('False', '0'):
            return queryset.filter(is_archived=False)
        return queryset


class SubmissionDateFilter(SimpleListFilter):
    title = 'Submission Date'
    parameter_name = 'submission_date'
    group = 'Application'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('7', 'Past 7 days'),
            ('30', 'Past 30 days'),
            ('90', 'Past 90 days'),
            ('this_year', 'This year'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        from datetime import timedelta
        if value == 'today':
            return queryset.filter(submission_date__date=timezone.localdate())
        if value == 'this_year':
            return queryset.filter(submission_date__year=timezone.now().year)
        return queryset.filter(submission_date__gte=timezone.now() - timedelta(days=int(value)))


class GenderFilter(SimpleListFilter):
    title = 'Gender'
    parameter_name = 'gender'
    group = 'Personal'

    def lookups(self, request, model_admin):
        return [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gender=self.value())
        return queryset


class ReligionFilter(GroupedFKFilter):
    title = 'Religion'
    parameter_name = 'religion'
    group = 'Personal'
    fk_model = Religion
    fk_field = 'religion'


class MaritalStatusFilter(GroupedFKFilter):
    title = 'Marital Status'
    parameter_name = 'marital_status'
    group = 'Personal'
    fk_model = MaritalStatus
    fk_field = 'marital_status'


class CommunityFilter(GroupedFKFilter):
    title = 'Community'
    parameter_name = 'community'
    group = 'Personal'
    fk_model = Community
    fk_field = 'community'


class ExServiceStatusFilter(GroupedFKFilter):
    title = 'Ex-Serviceman'
    parameter_name = 'ex_serviceman'
    group = 'Personal'
    fk_model = ExServiceStatus
    fk_field = 'ex_serviceman'


class OccupationFilter(GroupedFKFilter):
    title = 'Occupation'
    parameter_name = 'occupation'
    group = 'Personal'
    fk_model = Occupation
    fk_field = 'occupation'


class QualificationFilter(GroupedFKFilter):
    title = 'Qualification'
    parameter_name = 'qualification'
    group = 'Education'
    fk_model = Qualification
    fk_field = 'qualification'


class ProgramFilter(GroupedFKFilter):
    title = 'Program'
    parameter_name = 'program_opting'
    group = 'Education'
    fk_model = Program
    fk_field = 'program_opting'


class InstitutionFilter(SimpleListFilter):
    title = 'Institution'
    parameter_name = 'institution'
    group = 'Education'

    def lookups(self, request, model_admin):
        values = (model_admin.model.objects
                  .exclude(institution__isnull=True).exclude(institution='')
                  .values_list('institution', flat=True).distinct().order_by('institution'))
        return [(v, v) for v in values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(institution=self.value())
        return queryset


class YearOfPassingFilter(SimpleListFilter):
    title = 'Year of Passing'
    parameter_name = 'year_of_passing'
    group = 'Education'

    def lookups(self, request, model_admin):
        values = (model_admin.model.objects
                  .exclude(year_of_passing__isnull=True)
                  .values_list('year_of_passing', flat=True).distinct().order_by('-year_of_passing'))
        return [(v, str(v)) for v in values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(year_of_passing=self.value())
        return queryset


class StateFilter(GroupedFKFilter):
    title = 'State'
    parameter_name = 'state'
    group = 'Location'
    fk_model = State
    fk_field = 'state'


class DistrictFilter(GroupedFKFilter):
    title = 'District'
    parameter_name = 'district'
    group = 'Location'
    fk_model = District
    fk_field = 'district'


@admin.register(StudentApplication)
class StudentApplicationAdmin(admin.ModelAdmin):
    list_select_related = ('status', 'verification_status', 'state', 'district', 'country', 'religion', 'marital_status', 'community', 'ex_serviceman', 'occupation', 'qualification', 'training_partner')
    list_per_page = 50
    
    list_display = (
        'application_number', 'passport_photo_preview', 'full_name', 'father_name', 'mother_name', 
        'dob', 'gender', 'religion_display', 'marital_status_display', 'community_display', 'ex_serviceman_display', 
        'occupation_display', 'masked_aadhaar', 'mobile_number', 'alternative_mobile', 'email', 
        'country_display', 'state_display', 'district_display', 'pincode', 'institution_display', 'qualification_display', 
        'applying_qualification', 'registration_number', 'abc_id', 'hall_ticket_number', 
        'submission_date', 'status_badge', 'verification_badge'
    )
    
    list_filter = (
        ApplicationStatusFilter, VerificationStatusFilter, SubmissionDateFilter, ArchiveFilter,
        GenderFilter, ReligionFilter, MaritalStatusFilter, CommunityFilter,
        ExServiceStatusFilter, OccupationFilter,
        QualificationFilter, ProgramFilter, InstitutionFilter, YearOfPassingFilter,
        StateFilter, DistrictFilter,
    )
    
    autocomplete_fields = ('country', 'state', 'district')
    
    search_fields = (
        'application_number', 'full_name', 'aadhaar_number', 'mobile_number', 
        'registration_number', 'abc_id', 'institution'
    )
    
    date_hierarchy = 'submission_date'
    ordering = ('-submission_date',)
    
    inlines = [UploadedDocumentInline]
    
    readonly_fields = (
        'application_number', 'submission_date', 'last_updated', 
        'ip_address', 'browser_info', 'ack_pdf_link', 'ack_png_link', 'ack_jpg_link'
    )
    
    fieldsets = (
        ('System Information', {
            'fields': (
                ('application_number', 'status', 'verification_status'),
                ('submission_date', 'last_updated'),
                ('ip_address', 'browser_info'),
            ),
            'classes': ('collapse',)
        }),
        ('Verification Section', {
            'fields': (
                'remarks',
            )
        }),
        ('Acknowledgement Files', {
            'fields': ('ack_pdf_link', 'ack_png_link', 'ack_jpg_link'),
            'description': "Server-generated acknowledgement card downloads."
        }),
        ('Personal Details', {
            'fields': (
                'full_name', 'father_name', 'mother_name', 
                'dob', 'gender', 'marital_status', 
                'religion', 'community', 'nationality',
                'physically_handicapped', 'annual_income',
                'occupation', 'ex_serviceman',
                'aadhaar_number'
            )
        }),
        ('Contact Details', {
            'fields': (
                'mobile_number', 'alternative_mobile', 'email', 'communication_address', 
                'country', 'state', 'district', 'pincode'
            )
        }),
        ('Educational Details', {
            'fields': (
                'applying_qualification', 'qualification', 'custom_stream',
                'mode_of_qualification', 'completion_status', 'percentage',
                'year_of_passing', 'training_partner', 'batch_code',
                'institution', 'hall_ticket_number', 'registration_number', 'abc_id'
                , 'nielit_registration_number'
            )
        }),
    )

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if request.user.is_superuser:
            if 'masked_aadhaar' in list_display:
                idx = list_display.index('masked_aadhaar')
                list_display[idx] = 'aadhaar_number'
        return tuple(list_display)

    def get_readonly_fields(self, request, obj=None):
        ro_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            if 'masked_aadhaar' not in ro_fields:
                ro_fields.append('masked_aadhaar')
        return tuple(ro_fields)

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if not request.user.is_superuser:
            new_fieldsets = []
            for name, opts in fieldsets:
                if name == 'Personal Details':
                    fields = list(opts['fields'])
                    if 'aadhaar_number' in fields:
                        idx = fields.index('aadhaar_number')
                        fields[idx] = 'masked_aadhaar'
                    opts['fields'] = tuple(fields)
                new_fieldsets.append((name, opts))
            return tuple(new_fieldsets)
        return super().get_fieldsets(request, obj)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('documents')

    @admin.display(description="PHOTO")
    def passport_photo_preview(self, obj):
        doc = obj.documents.filter(doc_type__iexact='passport_photo').first()
        if doc and doc.compressed_file:
            url = doc.compressed_file.url
            return format_html('<a href="{}" target="_blank" style="white-space:nowrap;">View Photo</a>', url)
        return "-"

    def masked_aadhaar(self, obj):
        if obj.aadhaar_number and len(obj.aadhaar_number) == 12:
            return f"********{obj.aadhaar_number[-4:]}"
        return obj.aadhaar_number
    masked_aadhaar.short_description = "Aadhaar"

    def institution_display(self, obj):
        return obj.institution if obj.institution else "-"
    institution_display.short_description = 'Institution'

    @admin.display(description="Religion")
    def religion_display(self, obj): return str(obj.religion) if obj.religion else "-"

    @admin.display(description="Community")
    def community_display(self, obj): return str(obj.community) if obj.community else "-"

    @admin.display(description="Marital Status")
    def marital_status_display(self, obj): return str(obj.marital_status) if obj.marital_status else "-"

    @admin.display(description="Ex-Serviceman")
    def ex_serviceman_display(self, obj): return str(obj.ex_serviceman) if obj.ex_serviceman else "-"

    @admin.display(description="Occupation")
    def occupation_display(self, obj): return str(obj.occupation) if obj.occupation else "-"

    @admin.display(description="Country")
    def country_display(self, obj): return str(obj.country) if obj.country else "-"

    @admin.display(description="State")
    def state_display(self, obj): return str(obj.state) if obj.state else "-"

    @admin.display(description="District")
    def district_display(self, obj): return str(obj.district) if obj.district else "-"

    @admin.display(description="Qualification")
    def qualification_display(self, obj): return str(obj.qualification) if obj.qualification else "-"

    def status_badge(self, obj):
        if not obj.status:
            return format_html('<span style="color: gray; font-weight: bold;">UNKNOWN</span>')
        color_map = {'PENDING': '#ffc107', 'CORRECTION': '#fd7e14', 'INCOMPLETE': '#0dcaf0'}
        bg_color = color_map.get(obj.status.code, '#6c757d')
        text_color = '#000' if bg_color == '#ffc107' else '#fff'
        return format_html('<span style="background-color: {}; color: {}; padding: 4px 8px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>', bg_color, text_color, obj.status.name)
    status_badge.short_description = 'Status'
    
    def verification_badge(self, obj):
        if not obj.verification_status:
            return "-"
        color_map = {'PENDING': '#ffc107', 'VERIFIED': '#198754', 'CORRECTION': '#fd7e14'}
        bg_color = color_map.get(obj.verification_status.code, '#6c757d')
        text_color = '#000' if bg_color == '#ffc107' else '#fff'
        return format_html('<span style="background-color: {}; color: {}; padding: 4px 8px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>', bg_color, text_color, obj.verification_status.name)
    verification_badge.short_description = 'Verification'
    
    # ------------------------------------------------------------------
    # BULK ACTION SAFETY RULES
    # 1. Actions operate ONLY on the records selected in the changelist
    #    (the `queryset` argument). They never touch unselected records.
    # 2. Multi-step or irreversible actions (bulk edit, assign, email,
    #    delete) go through an intermediate confirmation page first.
    # 3. All writes are wrapped in transaction.atomic() - no partial updates.
    # 4. Every action reports exactly how many records it affected.
    # 5. Emails are sent fail_silently and only to students who have an
    #    email address; recipients without one are counted and reported.
    # 6. Status changes reuse the existing status fields/records
    #    (ApplicationStatus, VerificationStatus) - no duplicate systems.
    # 7. delete_selected lives ONLY in the "Danger Zone" group, which is
    #    always rendered LAST, and keeps Django's mandatory confirmation.
    # 8. No action name appears in more than one group.
    #
    # ACTION-MENU GROUPING RULES
    # - Each option belongs to exactly one group.
    # - Groups follow the menu order below; the "Danger Zone" group is
    #   always the last group in the dropdown.
    # - Group labels are rendered as <optgroup> inside the native admin
    #   <select>, so the standard Django Admin layout is unchanged.
    # ------------------------------------------------------------------
    ACTION_GROUPS = [
        ('Application Status', [
            ('mark_submitted', 'Mark as Submitted'),
            ('mark_draft', 'Mark as Draft'),
            ('mark_pending', 'Mark as Pending Review'),
            ('mark_correction_required', 'Mark as Correction Required'),
            ('mark_rejected', 'Mark as Rejected'),
            ('reset_status', 'Reset Status'),
        ]),
        ('Verification', [
            ('mark_verification_pending', 'Mark Verification Pending'),
            ('mark_verified', 'Mark Verified'),
            ('need_correction', 'Mark Need Correction'),
            ('clear_verification_status', 'Clear Verification Status'),
        ]),
        ('Documents', [
            ('download_documents', 'Download All Documents (ZIP)'),
            ('download_application_forms', 'Download Application Forms'),
            ('download_photos', 'Download Photos'),
            ('download_signatures', 'Download Signatures'),
            ('download_aadhaar', 'Download Aadhaar Documents'),
        ]),
        ('Export', [
            ('export_excel_action', 'Export Excel (.xlsx)'),
            ('export_csv_action', 'Export CSV (.csv)'),
            ('export_pdf', 'Export PDF'),
            ('export_zip', 'Export Complete Application Data (ZIP)'),
        ]),
        ('Student / Application', [
            ('view_selected', 'View Selected Applications'),
            ('edit_selected', 'Edit Selected Applications'),
            ('assign_training_partner', 'Assign Training Partner / ATC'),
            ('assign_program', 'Assign Program'),
            ('assign_batch_code', 'Assign Batch Code'),
            ('assign_institution', 'Assign Institution'),
        ]),
        ('Communication', [
            ('send_email', 'Send Email'),
            ('send_submission_confirmation', 'Send Submission Confirmation'),
            ('send_verification_notification', 'Send Verification Notification'),
            ('send_correction_request', 'Send Correction Request'),
        ]),
        ('Print', [
            ('print_applications', 'Print Selected Applications'),
            ('print_student_summary', 'Print Student Summary'),
        ]),
        ('Danger Zone', [
            ('archive_selected', 'Archive Selected'),
            ('restore_selected', 'Restore Selected'),
            ('delete_selected', 'Delete Selected'),
        ]),
    ]

    actions = [
        'mark_submitted', 'mark_draft', 'mark_pending', 'mark_correction_required',
        'mark_rejected', 'reset_status', 'mark_verification_pending', 'mark_verified',
        'need_correction', 'clear_verification_status', 'download_documents',
        'download_application_forms', 'download_photos', 'download_signatures',
        'download_aadhaar', 'export_excel_action', 'export_csv_action', 'export_pdf',
        'export_zip', 'view_selected', 'edit_selected', 'assign_training_partner',
        'assign_program', 'assign_batch_code', 'assign_institution', 'send_email',
        'send_submission_confirmation', 'send_verification_notification',
        'send_correction_request', 'print_applications', 'print_student_summary',
        'archive_selected', 'restore_selected',
    ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Safety net: keep the destructive delete action LAST, away from
        # frequently-used actions. It still uses Django's mandatory
        # confirmation dialog.
        if 'delete_selected' in actions:
            ordered = {k: v for k, v in actions.items() if k != 'delete_selected'}
            ordered['delete_selected'] = actions['delete_selected']
            return ordered
        return actions

    def get_action_choices(self, request, default_choices=None):
        """
        Returns the dropdown choices grouped into <optgroup> categories.
        The standard admin <select> widget renders nested choices as
        optgroups, so the existing Django Admin layout is preserved.
        """
        actions = self.get_actions(request)
        from django.contrib.admin.utils import model_format_dict
        fmt = model_format_dict(self.opts)
        ordered = []
        seen = set()
        for group_label, group_actions in self.ACTION_GROUPS:
            opts = []
            for name, _label in group_actions:
                if name in actions and name not in seen:
                    opts.append((name, actions[name][2] % fmt))
                    seen.add(name)
            if opts:
                ordered.append((group_label, opts))
        # Any actions not covered by the groups (e.g. global actions) are
        # appended flat so they remain usable.
        for name, (_func, _aname, desc) in actions.items():
            if name not in seen:
                ordered.append((name, desc % fmt))
        return [("", "---------")] + ordered

    def _get_status(self, code):
        return ApplicationStatus.objects.filter(code=code).first()

    def _action_form_hidden_fields(self, request, action_name):
        """Preserves the current selection when posting back to the changelist."""
        fields = []
        for pk in request.POST.getlist('_selected_action'):
            fields.append(('_selected_action', pk))
        if request.POST.get('select_across'):
            fields.append(('select_across', request.POST.get('select_across')))
        fields.append(('action', action_name))
        fields.append(('post', 'yes'))
        return fields

    def _action_context(self, request, action_name, title):
        return {
            'action_name': action_name,
            'title': title,
            'opts': self.model._meta,
            'hidden_fields': self._action_form_hidden_fields(request, action_name),
        }

    def mark_submitted(self, request, queryset):
        status = self._get_status('SUBMITTED')
        if not status:
            self.message_user(request, "Error: SUBMITTED status not found.", level=messages.ERROR)
            return
        updated = queryset.update(status=status)
        self.message_user(request, f"{updated} applications marked as Submitted.", level=messages.SUCCESS)
    mark_submitted.short_description = "Mark as Submitted"

    def mark_draft(self, request, queryset):
        draft_status = self._get_status('INCOMPLETE')
        if not draft_status:
            self.message_user(request, "Error: draft (INCOMPLETE) status not found.", level=messages.ERROR)
            return
        updated = queryset.update(status=draft_status)
        self.message_user(request, f"{updated} applications marked as Draft.", level=messages.SUCCESS)
    mark_draft.short_description = "Mark as Draft"

    def mark_pending(self, request, queryset):
        status = self._get_status('PENDING')
        if not status:
            self.message_user(request, "Error: PENDING status not found.", level=messages.ERROR)
            return
        updated = queryset.update(status=status)
        self.message_user(request, f"{updated} applications marked as Pending Review.", level=messages.SUCCESS)
    mark_pending.short_description = "Mark as Pending Review"

    def mark_correction_required(self, request, queryset):
        status = self._get_status('CORRECTION')
        if not status:
            self.message_user(request, "Error: CORRECTION status not found.", level=messages.ERROR)
            return
        updated = queryset.update(status=status)
        self.message_user(request, f"{updated} applications marked as Correction Required.", level=messages.SUCCESS)
    mark_correction_required.short_description = "Mark as Correction Required"

    def mark_rejected(self, request, queryset):
        status = self._get_status('REJECTED')
        if not status:
            self.message_user(request, "Error: REJECTED status not found.", level=messages.ERROR)
            return
        updated = queryset.update(status=status)
        self.message_user(request, f"{updated} applications marked as Rejected.", level=messages.SUCCESS)
    mark_rejected.short_description = "Mark as Rejected"

    def reset_status(self, request, queryset):
        updated = queryset.update(status=None)
        self.message_user(request, f"{updated} applications reset (status cleared).", level=messages.SUCCESS)
    reset_status.short_description = "Reset Status"

    def mark_verification_pending(self, request, queryset):
        status = VerificationStatus.objects.filter(code='PENDING').first()
        if not status:
            self.message_user(request, "Error: PENDING verification status not found.", level=messages.ERROR)
            return
        updated = queryset.update(verification_status=status)
        self.message_user(request, f"{updated} applications marked as Verification Pending.", level=messages.SUCCESS)
    mark_verification_pending.short_description = "Mark Verification Pending"

    def clear_verification_status(self, request, queryset):
        updated = queryset.update(verification_status=None)
        self.message_user(request, f"{updated} applications verification status cleared.", level=messages.SUCCESS)
    clear_verification_status.short_description = "Clear Verification Status"

    def view_selected(self, request, queryset):
        """Renders a read-only printable report of the selected applications."""
        queryset = queryset.select_related(
            'status', 'verification_status', 'training_partner', 'program_opting'
        ).prefetch_related('documents')
        context = self._action_context(request, 'view_selected', 'View selected applications')
        context['applications'] = queryset
        return render(request, 'admin/registrations/studentapplication/view_selected.html', context)
    view_selected.short_description = "View Selected"

    def edit_selected(self, request, queryset):
        """Bulk-edit common fields on the selected applications."""
        editable_fields = [
            'status', 'verification_status', 'training_partner',
            'program_opting', 'batch_code', 'institution', 'remarks',
        ]
        if 'post' not in request.POST:
            context = self._action_context(request, 'edit_selected', 'Bulk edit selected applications')
            context['applications'] = queryset
            context['statuses'] = ApplicationStatus.objects.order_by('id')
            context['verification_statuses'] = VerificationStatus.objects.order_by('id')
            context['training_partners'] = TrainingPartner.objects.order_by('name')
            from masterdata.models import Program
            context['programs'] = Program.objects.order_by('name')
            return render(request, 'admin/registrations/studentapplication/edit_selected.html', context)

        with transaction.atomic():
            updated = 0
            for app in queryset:
                changed = False
                for fname in editable_fields:
                    if request.POST.get('set_' + fname):
                        raw = request.POST.get('value_' + fname, '').strip()
                        if not raw:
                            continue
                        if fname in ('batch_code', 'institution', 'remarks'):
                            setattr(app, fname, raw)
                        elif raw.isdigit():
                            setattr(app, fname + '_id', raw)
                        else:
                            continue
                        changed = True
                if changed:
                    app.save(update_fields=editable_fields)
                    updated += 1
        self.message_user(request, f"{updated} applications updated.", level=messages.SUCCESS)
    edit_selected.short_description = "Edit Selected"

    def send_email(self, request, queryset):
        """Sends an email to the selected students who have an address."""
        if 'post' not in request.POST:
            context = self._action_context(request, 'send_email', 'Send email to selected students')
            context['applications'] = queryset
            return render(request, 'admin/registrations/studentapplication/send_email.html', context)

        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('message', '').strip()
        if not subject or not body:
            context = self._action_context(request, 'send_email', 'Send email to selected students')
            context['applications'] = queryset
            context['error'] = 'Subject and message are both required.'
            context['subject'] = subject
            context['body'] = body
            return render(request, 'admin/registrations/studentapplication/send_email.html', context)

        from django.core.mail import send_mail
        from django.conf import settings

        with_email = queryset.exclude(email__isnull=True).exclude(email='')
        no_email = queryset.count() - with_email.count()
        sent = 0
        for app in with_email:
            try:
                send_mail(
                    subject,
                    f"Dear {app.full_name},\n\n{body}\n\nRegards,\nCSC Admin Team",
                    settings.DEFAULT_FROM_EMAIL,
                    [app.email],
                    fail_silently=True,
                )
                sent += 1
            except Exception:
                continue
        msg = f"Email sent to {sent} applicant(s)."
        if no_email:
            msg += f" {no_email} selected had no email address and were skipped."
        self.message_user(request, msg, level=messages.SUCCESS)
    send_email.short_description = "Send Email"

    def assign_training_partner(self, request, queryset):
        """Assigns a Training Partner/ATC (and optional batch) to the selection."""
        if 'post' not in request.POST:
            context = self._action_context(request, 'assign_training_partner', 'Assign training partner / ATC')
            context['applications'] = queryset
            context['training_partners'] = TrainingPartner.objects.order_by('name')
            return render(request, 'admin/registrations/studentapplication/assign_training_partner.html', context)

        partner_id = request.POST.get('training_partner', '')
        partner = TrainingPartner.objects.filter(pk=partner_id).first() if partner_id.isdigit() else None
        batch_code = request.POST.get('batch_code', '').strip()
        if not partner:
            context = self._action_context(request, 'assign_training_partner', 'Assign training partner / ATC')
            context['applications'] = queryset
            context['training_partners'] = TrainingPartner.objects.order_by('name')
            context['error'] = 'Please select a training partner.'
            return render(request, 'admin/registrations/studentapplication/assign_training_partner.html', context)

        with transaction.atomic():
            updated = queryset.update(training_partner=partner, batch_code=batch_code or None)
        self.message_user(
            request,
            f"{updated} applications assigned to {partner.name}." + (f" Batch: {batch_code}" if batch_code else ""),
            level=messages.SUCCESS,
        )
    assign_training_partner.short_description = "Assign Training Partner"

    def _assign_field(self, request, queryset, action_name, label, model_field,
                      choices, is_select=True, field_name=None):
        """Generic intermediate form to set one field on the selection."""
        field_name = field_name or model_field
        context = self._action_context(request, action_name, f"Assign {label} to {queryset.count()} selected application(s)")
        context.update({
            'applications': queryset,
            'label': label,
            'field_name': field_name,
            'is_select': is_select,
            'choices': [(c.pk, str(c)) for c in choices],
        })
        if 'post' not in request.POST:
            return render(request, 'admin/registrations/studentapplication/assign_field.html', context)

        raw = request.POST.get(field_name, '').strip()
        if is_select:
            value = choices.filter(pk=raw).first() if raw.isdigit() else None
            if not value:
                context['error'] = f'Please select a {label.lower()}.'
                return render(request, 'admin/registrations/studentapplication/assign_field.html', context)
            with transaction.atomic():
                updated = queryset.update(**{model_field: value})
            self.message_user(request, f"{updated} applications assigned: {label} = {value}.", level=messages.SUCCESS)
        else:
            if not raw:
                context['error'] = f'Please enter a {label.lower()}.'
                return render(request, 'admin/registrations/studentapplication/assign_field.html', context)
            with transaction.atomic():
                updated = queryset.update(**{model_field: raw})
            self.message_user(request, f"{updated} applications updated: {label} = {raw}.", level=messages.SUCCESS)

    def assign_program(self, request, queryset):
        from masterdata.models import Program
        return self._assign_field(request, queryset, 'assign_program', 'Program', 'program_opting',
                                  Program.objects.order_by('name'), field_name='program')
    assign_program.short_description = "Assign Program"

    def assign_batch_code(self, request, queryset):
        return self._assign_field(request, queryset, 'assign_batch_code', 'Batch Code', 'batch_code',
                                  [], is_select=False, field_name='batch_code')
    assign_batch_code.short_description = "Assign Batch Code"

    def assign_institution(self, request, queryset):
        return self._assign_field(request, queryset, 'assign_institution', 'Institution', 'institution',
                                  [], is_select=False, field_name='institution')
    assign_institution.short_description = "Assign Institution"

    def _send_canned_email(self, request, queryset, action_name, title, subject, body):
        """Sends a fixed subject/body email after an explicit confirmation page."""
        recipients = queryset.exclude(email__isnull=True).exclude(email='')
        no_email_count = queryset.count() - recipients.count()
        if 'post' not in request.POST:
            context = self._action_context(request, action_name, title)
            context['applications'] = queryset
            context['recipients'] = recipients
            context['no_email_count'] = no_email_count
            context['subject'] = subject
            context['body'] = body
            return render(request, 'admin/registrations/studentapplication/send_email_confirm.html', context)

        from django.core.mail import send_mail
        from django.conf import settings
        sent = 0
        for app in recipients:
            try:
                send_mail(
                    subject.format(app=app),
                    body.format(app=app),
                    settings.DEFAULT_FROM_EMAIL,
                    [app.email],
                    fail_silently=True,
                )
                sent += 1
            except Exception:
                continue
        msg = f"Email sent to {sent} applicant(s)."
        if no_email_count:
            msg += f" {no_email_count} selected had no email address and were skipped."
        self.message_user(request, msg, level=messages.SUCCESS)

    def send_submission_confirmation(self, request, queryset):
        return self._send_canned_email(
            request, queryset, 'send_submission_confirmation',
            'Send submission confirmation to selected students',
            "Application Submitted - {app.application_number}",
            "Dear {app.full_name},\n\nYour application ({app.application_number}) has been received and submitted successfully. Thank you for applying.\n\nRegards,\nCSC Admin Team",
        )
    send_submission_confirmation.short_description = "Send Submission Confirmation"

    def send_verification_notification(self, request, queryset):
        return self._send_canned_email(
            request, queryset, 'send_verification_notification',
            'Send verification notification to selected students',
            "Application Verified - {app.application_number}",
            "Dear {app.full_name},\n\nYour application ({app.application_number}) has been verified successfully.\n\nRegards,\nCSC Admin Team",
        )
    send_verification_notification.short_description = "Send Verification Notification"

    def send_correction_request(self, request, queryset):
        return self._send_canned_email(
            request, queryset, 'send_correction_request',
            'Send correction request to selected students',
            "Correction Required - {app.application_number}",
            "Dear {app.full_name},\n\nYour application ({app.application_number}) needs corrections. Please contact the office or submit the required corrections.\n\nRegards,\nCSC Admin Team",
        )
    send_correction_request.short_description = "Send Correction Request"

    def print_applications(self, request, queryset):
        """Printable page of the selected applications (auto-triggers print)."""
        queryset = queryset.select_related(
            'status', 'verification_status', 'training_partner', 'program_opting'
        ).prefetch_related('documents')
        context = self._action_context(request, 'print_applications', 'Print selected applications')
        context['applications'] = queryset
        return render(request, 'admin/registrations/studentapplication/print_applications.html', context)
    print_applications.short_description = "Print Selected Applications"

    def print_student_summary(self, request, queryset):
        """Compact printable summary of the selected applications."""
        queryset = queryset.select_related(
            'status', 'verification_status', 'training_partner', 'program_opting', 'state', 'district'
        )
        context = self._action_context(request, 'print_student_summary', 'Print student summary')
        context['applications'] = queryset
        return render(request, 'admin/registrations/studentapplication/print_student_summary.html', context)
    print_student_summary.short_description = "Print Student Summary"

    def archive_selected(self, request, queryset):
        with transaction.atomic():
            updated = queryset.update(is_archived=True)
        self.message_user(request, f"{updated} applications archived.", level=messages.SUCCESS)
    archive_selected.short_description = "Archive Selected"

    def restore_selected(self, request, queryset):
        with transaction.atomic():
            updated = queryset.update(is_archived=False)
        self.message_user(request, f"{updated} applications restored.", level=messages.SUCCESS)
    restore_selected.short_description = "Restore Selected"

    def mark_verified(self, request, queryset):
        verified_status = VerificationStatus.objects.filter(code='VERIFIED').first()
        if not verified_status:
            self.message_user(request, "Error: VERIFIED status not found.", level=messages.ERROR)
            return
        updated = queryset.update(verification_status=verified_status)
        self.message_user(request, f"{updated} applications marked as verified.", level=messages.SUCCESS)
    mark_verified.short_description = "Mark Verified"
    
    def need_correction(self, request, queryset):
        correction_status = VerificationStatus.objects.filter(code='CORRECTION').first()
        if not correction_status:
            self.message_user(request, "Error: CORRECTION status not found.", level=messages.ERROR)
            return
        updated = queryset.update(verification_status=correction_status)
        self.message_user(request, f"{updated} applications marked as need correction.", level=messages.SUCCESS)
    need_correction.short_description = "Need Correction"
    
    def export_excel_action(self, request, queryset):
        from utilities.export_generator import generate_full_excel_export
        from django.http import HttpResponse
        excel_data = generate_full_excel_export(queryset, request)
        response = HttpResponse(excel_data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="applications_export.xlsx"'
        return response
    export_excel_action.short_description = "Export to Excel (.xlsx)"
    
    def export_csv_action(self, request, queryset):
        from utilities.export_generator import generate_full_csv_export
        from django.http import HttpResponse
        csv_data = generate_full_csv_export(queryset, request)
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="applications_export.csv"'
        return response
    export_csv_action.short_description = "Export to CSV (.csv)"

    def export_pdf(self, request, queryset):
        self.message_user(request, "PDF export initiated (Not fully implemented yet).", level=messages.INFO)
    export_pdf.short_description = "Export PDF"

    def export_zip(self, request, queryset):
        import zipfile
        import io
        import os
        from datetime import datetime
        from django.http import HttpResponse
        from utilities.export_helpers import generate_student_details_excel, generate_student_information_pdf
        from utilities.folder_manager import get_student_folder_name

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for app in queryset.prefetch_related('documents'):
                if app.storage_folder:
                    app_folder = f"{app.storage_folder}/"
                else:
                    try:
                        app_folder = f"{get_student_folder_name(app.aadhaar_number, app.full_name)}/"
                    except ValueError:
                        safe_name = str(app.full_name).replace(" ", "_")
                        aadhaar = app.aadhaar_number if app.aadhaar_number else "NoAadhaar"
                        app_folder = f"{aadhaar}_{safe_name}/"
                
                try:
                    excel_data = generate_student_details_excel(app)
                    zip_file.writestr(f"{app_folder}Student_Details.xlsx", excel_data)
                except Exception as e:
                    print(f"Error generating Excel for {app.application_number}: {e}")
                
                try:
                    pdf_data = generate_student_information_pdf(app)
                    zip_file.writestr(f"{app_folder}Student_Information.pdf", pdf_data)
                except Exception as e:
                    print(f"Error generating PDF for {app.application_number}: {e}")
                
                if app.acknowledgement_pdf and app.acknowledgement_pdf.name:
                    if os.path.exists(app.acknowledgement_pdf.path):
                        zip_file.write(app.acknowledgement_pdf.path, arcname=f"{app_folder}Acknowledgement.pdf")
                
                doc_folders = {
                    'passport_photo': 'Passport_Photo',
                    'signature': 'Signature',
                    'thumb_impression': 'Left_Thumb',
                    'aadhaar_pdf': 'Aadhaar',
                    'community_certificate': 'Community_Certificate',
                    'registration_screenshot': 'Registration_Screenshot',
                    'abc_screenshot': 'ABC_ID',
                    'supporting_documents': 'Supporting_Documents'
                }
                
                for doc in app.documents.all():
                    folder_name = doc_folders.get(doc.doc_type, doc.doc_type.capitalize())
                    
                    if doc.original_file and doc.original_file.name:
                        if os.path.exists(doc.original_file.path):
                            ext = doc.original_file.name.split('.')[-1]
                            zip_file.write(
                                doc.original_file.path, 
                                arcname=f"{app_folder}{folder_name}/original.{ext}"
                            )
                            
                    if doc.compressed_file and doc.compressed_file.name:
                        if os.path.exists(doc.compressed_file.path):
                            ext = doc.compressed_file.name.split('.')[-1]
                            zip_file.write(
                                doc.compressed_file.path, 
                                arcname=f"{app_folder}{folder_name}/optimized.{ext}"
                            )

        buffer.seek(0)
        date_str = datetime.now().strftime("%d-%m-%Y")
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="Student_Applications_{date_str}.zip"'
        return response
    export_zip.short_description = "Export ZIP"
    
    def _app_folder_name(self, app):
        from utilities.folder_manager import get_student_folder_name
        if app.storage_folder:
            return f"{app.storage_folder}/"
        try:
            return f"{get_student_folder_name(app.aadhaar_number, app.full_name)}/"
        except ValueError:
            safe_name = str(app.full_name).replace(" ", "_")
            aadhaar = app.aadhaar_number if app.aadhaar_number else "NoAadhaar"
            return f"{aadhaar}_{safe_name}/"

    def _zip_documents_response(self, queryset, allowed_doc_types=None, prefix='Documents', extra_files=None):
        """Builds a ZIP of uploaded documents (optionally filtered by doc_type)."""
        import zipfile
        import io
        import os
        from datetime import datetime
        from django.http import HttpResponse

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for app in queryset.prefetch_related('documents'):
                folder = self._app_folder_name(app)
                docs = app.documents.all()
                if allowed_doc_types is not None:
                    docs = docs.filter(doc_type__in=allowed_doc_types)
                for doc in docs:
                    f = doc.original_file
                    if f and f.name and os.path.exists(f.path):
                        ext = f.name.split('.')[-1]
                        zf.write(f.path, arcname=f"{folder}{doc.doc_type}/{doc.pk}.{ext}")
                if extra_files:
                    for arcname, path in extra_files(app):
                        if path and os.path.exists(path):
                            zf.write(path, arcname=f"{folder}{arcname}")

        buffer.seek(0)
        date_str = datetime.now().strftime('%d-%m-%Y')
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{prefix}_{date_str}.zip"'
        return response

    DOC_TYPE_ALIASES = {
        'photos': {'Passport_Photo', 'Passport'},
        'signatures': {'Signature', 'Father_Signature'},
        'aadhaar': {'Aadhaar'},
    }

    def download_documents(self, request, queryset):
        return self._zip_documents_response(queryset, None, 'All_Documents')
    download_documents.short_description = "Download All Documents (ZIP)"

    def download_application_forms(self, request, queryset):
        return self._zip_documents_response(
            queryset,
            allowed_doc_types=set(),
            prefix='Application_Forms',
            extra_files=lambda app: ([("Acknowledgement.pdf", app.acknowledgement_pdf.path)]
                                     if app.acknowledgement_pdf and app.acknowledgement_pdf.name else []),
        )
    download_application_forms.short_description = "Download Application Forms"

    def download_photos(self, request, queryset):
        return self._zip_documents_response(queryset, self.DOC_TYPE_ALIASES['photos'], 'Photos')
    download_photos.short_description = "Download Photos"

    def download_signatures(self, request, queryset):
        return self._zip_documents_response(queryset, self.DOC_TYPE_ALIASES['signatures'], 'Signatures')
    download_signatures.short_description = "Download Signatures"

    def download_aadhaar(self, request, queryset):
        return self._zip_documents_response(queryset, self.DOC_TYPE_ALIASES['aadhaar'], 'Aadhaar')
    download_aadhaar.short_description = "Download Aadhaar Documents"

    def ack_pdf_link(self, obj):
        if obj.acknowledgement_pdf:
            return format_html('<a href="{}" target="_blank" class="button" style="background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 4px;">Download PDF</a>', obj.acknowledgement_pdf.url)
        return "Not Generated"
    ack_pdf_link.short_description = "A4 PDF"

    def ack_png_link(self, obj):
        if obj.acknowledgement_png:
            return format_html('<a href="{}" target="_blank" class="button" style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px;">Download PNG</a>', obj.acknowledgement_png.url)
        return "Not Generated"
    ack_png_link.short_description = "High-Res PNG"

    def ack_jpg_link(self, obj):
        if obj.acknowledgement_jpg:
            return format_html('<a href="{}" target="_blank" class="button" style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px;">Download JPG</a>', obj.acknowledgement_jpg.url)
        return "Not Generated"
    ack_jpg_link.short_description = "High-Res JPG"

from django.contrib.admin.sites import AdminSite

original_get_app_list = AdminSite.get_app_list

def custom_get_app_list(self, request, app_label=None):
    app_list = original_get_app_list(self, request, app_label)
    app_order = {
        'auth': 1,
        'registrations': 2,
        'masterdata': 3,
    }
    app_list.sort(key=lambda x: app_order.get(x['app_label'], 999))
    return app_list

AdminSite.get_app_list = custom_get_app_list
