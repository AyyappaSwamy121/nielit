from django.urls import path
from . import views

urlpatterns = [
    path('process-image/', views.process_image, name='process_image'),
]
