from django.urls import path
from . import views

urlpatterns = [
    path('api/states/', views.get_states, name='api_get_states'),
    path('api/districts/', views.get_districts, name='api_get_districts'),
]
