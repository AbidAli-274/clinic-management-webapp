from django.urls import path

from .views import (
    EditPatientView,
    PatientCreateView,
    PatientHistoryView,
    PatientSearchView,
)

app_name = "patients"

urlpatterns = [
    path("create/", PatientCreateView.as_view(), name="patient_create"),
    path("", PatientSearchView.as_view(), name="search"),
    path("<int:patient_id>/", PatientHistoryView.as_view(), name="history"),
    path("<int:patient_id>/edit/", EditPatientView.as_view(), name="edit_patient"),
]
