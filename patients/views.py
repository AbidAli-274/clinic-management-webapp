from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import Patient
from .forms import PatientForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView,UpdateView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from appointments.models import Patient, Consultancy, Session
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


class PatientCreateView(LoginRequiredMixin,CreateView):
    model = Patient
    form_class = PatientForm  
    template_name = 'patient_create.html' 
    success_url = reverse_lazy('patients:patient_create')
    login_url = reverse_lazy('accounts:login') 

    def form_valid(self, form):
        form.instance.organization = self.request.user.organization
        return super().form_valid(form)


class PatientSearchView(LoginRequiredMixin, ListView):
  model = Patient
  template_name = 'patient_search.html'
  context_object_name = 'patients'
  login_url = reverse_lazy('accounts:login')
  paginate_by = 10
  
  def get_queryset(self):
      queryset = Patient.objects.all().order_by('-created_at')
      query = self.request.GET.get('q')
      
      if query:
          # Search by name (partial match) or phone number (exact match)
          queryset = queryset.filter(
              Q(name__icontains=query) | Q(phone_number__iexact=query)
          )
      
      return queryset
  
  def get_context_data(self, **kwargs):
      context = super().get_context_data(**kwargs)
      context['query'] = self.request.GET.get('q', '')
      return context


class PatientHistoryView(LoginRequiredMixin, TemplateView):
    template_name = 'patient_history.html'
    login_url = reverse_lazy('accounts:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get patient by ID
        patient_id = self.kwargs.get('patient_id')
        patient = get_object_or_404(Patient, id=patient_id)
        
        # Get all consultancies for this patient
        consultancies = Consultancy.objects.filter(
            patient=patient
        ).select_related('referred_doctor').order_by('-date_time')
        
        # Get all sessions for this patient
        sessions = Session.objects.filter(
            patient=patient
        ).select_related('doctor', 'consultancy').order_by('-date_time')
        
        # Calculate statistics
        total_consultancies = consultancies.count()
        total_sessions = sessions.count()
        
        # Calculate financial data
        total_spent = 0
        total_discount = 0
        
        for consultancy in consultancies:
            total_spent += float(consultancy.consultancy_fee)
            total_discount += float(consultancy.discount)
        
        for session in sessions:
            total_spent += float(session.session_fee)
        
        # Get status counts
        consultancy_status = {
            'pending': consultancies.filter(status='Pending').count(),
            'continue': consultancies.filter(status='Continue').count(),
            'completed': consultancies.filter(status='Completed').count(),
        }
        
        session_status = {
            'pending': sessions.filter(status='Pending').count(),
            'continue': sessions.filter(status='Continue').count(),
            'completed': sessions.filter(status='Completed').count(),
        }
        
        # Prepare consultancy data
        consultancy_data = []
        for consultancy in consultancies:
            # Get related sessions for this consultancy
            related_sessions = Session.objects.filter(
                consultancy=consultancy
            ).select_related('doctor').order_by('-date_time')
            
            consultancy_data.append({
                'id': consultancy.id,
                'date_time': consultancy.date_time,
                'chief_complaint': consultancy.chief_complaint,
                'doctor': consultancy.referred_doctor if consultancy.referred_doctor else 'N/A',
                'fee': float(consultancy.consultancy_fee),
                'discount': float(consultancy.discount),
                'net_amount': float(consultancy.consultancy_fee) - float(consultancy.discount),
                'sessions_planned': consultancy.number_of_sessions,
                'sessions_completed': related_sessions.filter(status='Completed').count(),
                'status': consultancy.status,
                'related_sessions': related_sessions,
            })
        
        # Prepare session data
        session_data = []
        for session in sessions:
            session_data.append({
                'id': session.id,
                'date_time': session.date_time,
                'doctor': session.doctor if session.doctor else 'N/A',
                'fee': float(session.session_fee),
                'status': session.status,
                'feedback': session.feedback,
                'consultancy_id': session.consultancy.id if session.consultancy else None,
            })
        
        # Pagination for consultancies
        consultancies_page = self.request.GET.get('consultancies_page', 1)
        consultancies_paginator = Paginator(consultancy_data, 5)  # Show 5 consultancies per page
        
        try:
            consultancies_page_obj = consultancies_paginator.page(consultancies_page)
        except PageNotAnInteger:
            consultancies_page_obj = consultancies_paginator.page(1)
        except EmptyPage:
            consultancies_page_obj = consultancies_paginator.page(consultancies_paginator.num_pages)
        
        # Pagination for sessions
        sessions_page = self.request.GET.get('sessions_page', 1)
        sessions_paginator = Paginator(session_data, 10)  # Show 10 sessions per page
        
        try:
            sessions_page_obj = sessions_paginator.page(sessions_page)
        except PageNotAnInteger:
            sessions_page_obj = sessions_paginator.page(1)
        except EmptyPage:
            sessions_page_obj = sessions_paginator.page(sessions_paginator.num_pages)
        
        context.update({
            'patient': patient,
            'total_consultancies': total_consultancies,
            'total_sessions': total_sessions,
            'total_spent': total_spent,
            'total_discount': total_discount,
            'net_spent': total_spent - total_discount,
            'consultancy_status': consultancy_status,
            'session_status': session_status,
            'consultancy_data': consultancies_page_obj,
            'session_data': sessions_page_obj,
            'consultancies_paginator': consultancies_paginator,
            'consultancies_page_obj': consultancies_page_obj,
            'sessions_paginator': sessions_paginator,
            'sessions_page_obj': sessions_page_obj,
        })
        
        return context


class EditPatientView(LoginRequiredMixin, UpdateView):
    model = Patient
    template_name = 'edit_patient.html'
    fields = ['name', 'phone_number', 'gender', 'city']
    pk_url_kwarg = 'patient_id'
    login_url = reverse_lazy('accounts:login')
    
    def get_success_url(self):
        return reverse('patients:history', kwargs={'patient_id': self.object.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object
        return context