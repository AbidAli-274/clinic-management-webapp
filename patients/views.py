from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import Patient
from .forms import PatientForm


class PatientCreateView(CreateView):
    model = Patient
    form_class = PatientForm  
    template_name = 'patient_create.html' 
    success_url = reverse_lazy('patients:patient_create')
