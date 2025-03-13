from django.urls import path
from .views import PatientCreateView

app_name = "patients"

urlpatterns = [
    path('create/', PatientCreateView.as_view(), name='patient_create'),
]
