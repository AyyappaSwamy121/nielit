from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    
    # Placeholder URLs for Sidebar
    path('applications/', views.application_list, name='application_list'),
    path('applications/pending/', views.application_pending, name='application_pending'),
    path('students/', views.student_directory, name='student_directory'),
    path('verification/', views.verification_desk, name='verification_desk'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('exports/', views.export_center, name='export_center'),
    path('master-data/', views.master_data, name='master_data'),
    path('settings/', views.settings_dashboard, name='settings_dashboard'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    
    # Export Endpoints
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/db/', views.export_db, name='export_db'),
]
