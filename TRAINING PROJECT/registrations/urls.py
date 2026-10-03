from django.urls import path
from . import views

urlpatterns = [
    path('', views.registration_view, name='registration'),
    path('api/submit/', views.submit_application, name='submit_application'),
    path('preview/', views.preview_application, name='preview_application'),
    path('final-submit/', views.final_submit, name='final_submit'),
    path('success/', views.success_view, name='success'),
    path('success/document/<str:token>/<int:doc_id>/download/', views.download_document, name='download_document'),
    path('success/document/<str:token>/download-all/', views.download_all_documents, name='download_all_documents'),
    path('api/check-duplicate/', views.check_duplicate, name='check_duplicate'),
    path('api/states/', views.get_states, name='get_states'),
    path('api/districts/', views.get_districts, name='get_districts'),
    path('api/auto-save/', views.auto_save_field, name='auto_save_field'),
    path('api/pincode-lookup/', views.pincode_lookup, name='pincode_lookup'),
    path('api/get-batch-code/', views.get_batch_code, name='get_batch_code'),
    path('api/async-upload-pdf/', views.async_upload_pdf, name='async_upload_pdf'),
]
