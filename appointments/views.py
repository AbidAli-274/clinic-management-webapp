from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import Consultancy, Session
from .forms import ConsultancyForm, SessionForm  
from django.utils import timezone

class ConsultancyCreateView(CreateView):
    model = Consultancy
    form_class = ConsultancyForm
    template_name = 'consultancy_create.html'
    success_url = reverse_lazy('appointments:consultancy_create') 

    def form_valid(self, form):
        # Set the current date and time for date_time field
        form.instance.date_time = timezone.now()
        
        return super().form_valid(form)
    

class SessionCreateView(CreateView):
    model = Session
    form_class = SessionForm
    template_name = 'session_create.html'
    success_url = reverse_lazy('appointments:session_create')  
    
    
    def form_valid(self, form):
        form.instance.date_time = timezone.now()
        
        return super().form_valid(form)
