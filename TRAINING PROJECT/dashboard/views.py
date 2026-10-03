from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from registrations.models import StudentApplication, UploadedDocument
from masterdata.models import State, District, Program, Qualification, ApplicationStatus, VerificationStatus
from django.core.paginator import Paginator
from django.db.models import Q

@login_required
@user_passes_test(lambda u: u.is_staff)
def dashboard_home(request):
    """
    Renders the main dashboard with live ORM data metrics.
    """
    # Fetch base querysets
    applications = StudentApplication.objects.all()
    
    # Calculate Primary Metrics
    total_apps = applications.count()
    pending_apps = applications.filter(status__code='PENDING').count()
    approved_apps = applications.filter(status__code='APPROVED').count()
    rejected_apps = applications.filter(status__code='REJECTED').count()
    
    # Demographics & Geography
    male_count = applications.filter(gender='Male').count()
    female_count = applications.filter(gender='Female').count()
    total_states = State.objects.count()
    total_districts = District.objects.count()
    
    # Academic Metrics
    total_institutions = applications.values('institution').distinct().count()
    total_programs = Program.objects.count()
    
    # Storage Metrics (Dummy for now until physical disk check implemented)
    total_docs = UploadedDocument.objects.count()
    
    # Recent Applications Table Data
    recent_apps = applications.order_by('-submission_date')[:5]

    context = {
        'metrics': {
            'total_apps': total_apps,
            'pending_apps': pending_apps,
            'approved_apps': approved_apps,
            'rejected_apps': rejected_apps,
            'male_count': male_count,
            'female_count': female_count,
            'total_states': total_states,
            'total_districts': total_districts,
            'total_institutions': total_institutions,
            'total_programs': total_programs,
            'total_docs': total_docs,
        },
        'recent_apps': recent_apps,
    }
    return render(request, 'dashboard/index.html', context)


# ==========================================
# PLACEHOLDER VIEWS TO ELIMINATE 404s
# ==========================================

@login_required
@user_passes_test(lambda u: u.is_staff)
def application_list(request):
    """
    Renders the Applications table with filtering, search, and pagination.
    """
    applications = StudentApplication.objects.select_related(
        'program_opting', 'status', 'verification_status', 'state', 'district', 'qualification'
    ).prefetch_related('documents').order_by('-submission_date')
    
    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        applications = applications.filter(
            Q(application_number__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(aadhaar_number__icontains=search_query) |
            Q(mobile_number__icontains=search_query) |
            Q(registration_number__icontains=search_query) |
            Q(abc_id__icontains=search_query) |
            Q(hall_ticket_number__icontains=search_query) |
            Q(institution__icontains=search_query)
        )
    
    # Filters
    state_id = request.GET.get('state')
    district_id = request.GET.get('district')
    program_id = request.GET.get('program')
    status_id = request.GET.get('status')
    v_status_id = request.GET.get('verification_status')
    
    if state_id:
        applications = applications.filter(state_id=state_id)
    if district_id:
        applications = applications.filter(district_id=district_id)
    if program_id:
        applications = applications.filter(program_opting_id=program_id)
    if status_id:
        applications = applications.filter(status_id=status_id)
    if v_status_id:
        applications = applications.filter(verification_status_id=v_status_id)

    # Pagination
    paginator = Paginator(applications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Reference data for filters
    context = {
        'title': 'All Applications',
        'page_obj': page_obj,
        'states': State.objects.all(),
        'programs': Program.objects.all(),
        'statuses': ApplicationStatus.objects.all(),
        'v_statuses': VerificationStatus.objects.all(),
        # Pass current filters to preserve in UI
        'current_search': search_query,
        'current_state': state_id,
        'current_district': district_id,
        'current_program': program_id,
        'current_status': status_id,
        'current_v_status': v_status_id,
    }
    return render(request, 'dashboard/applications.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def application_pending(request):
    return render(request, 'dashboard/placeholder.html', {'title': 'Pending Applications'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def student_directory(request):
    return render(request, 'dashboard/placeholder.html', {'title': 'Student Directory'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def verification_desk(request):
    return render(request, 'dashboard/placeholder.html', {'title': 'Verification Desk'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def reports_dashboard(request):
    return render(request, 'dashboard/placeholder.html', {'title': 'Custom Reports'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def export_center(request):
    return render(request, 'dashboard/placeholder.html', {'title': 'Export Center'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def master_data(request):
    return render(request, 'dashboard/placeholder.html', {'title': 'Master Data'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def settings_dashboard(request):
    return render(request, 'dashboard/placeholder.html', {'title': 'Platform Settings'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def audit_logs(request):
    return render(request, 'dashboard/placeholder.html', {'title': 'Audit Logs'})

import csv
import os
from django.http import HttpResponse, FileResponse
from django.conf import settings

@login_required
@user_passes_test(lambda u: u.is_staff)
def export_csv(request):
    """
    Generates a live CSV export of all student applications using the full comprehensive export logic.
    """
    from utilities.export_generator import generate_full_csv_export
    from django.http import HttpResponse
    
    applications = StudentApplication.objects.all()
    csv_data = generate_full_csv_export(applications, request)
    
    response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="applications_export.csv"'
    return response

@login_required
@user_passes_test(lambda u: u.is_staff)
def export_db(request):
    """
    Securely downloads the live db.sqlite3 database backup.
    """
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    if os.path.exists(db_path):
        response = FileResponse(open(db_path, 'rb'), content_type='application/x-sqlite3')
        response['Content-Disposition'] = 'attachment; filename="backup_db.sqlite3"'
        return response
    return HttpResponse("Database file not found.", status=404)

