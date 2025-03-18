from django.shortcuts import render
from django.views.generic import FormView
from accounts.models import Organization, UserProfile
from .forms import EmailAuthenticationForm, OrganizationForm, UserProfileForm
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import resolve_url
from django.contrib.auth import login as auth_login
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.contrib.auth import logout as auth_logout
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView
from django.http import HttpResponseRedirect
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic.base import TemplateView
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView  
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import datetime, time
from appointments.models import Session, Consultancy
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.views.generic import ListView, DetailView
from django.contrib.auth import get_user_model


@login_required(login_url="accounts:login")
def home(request):
    """Render the home page with additional data from the waiting screen."""
    
    # Get today's date with time set to beginning of day
    today = timezone.now().date()
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)
    
    # Get pending and continue sessions for today
    pending_sessions = Session.objects.filter(
        date_time__range=(today_start, today_end),
        status__in=['Pending', 'Continue']
    ).select_related('patient')
    
    # Get pending and continue consultancies for today
    pending_consultancies = Consultancy.objects.filter(
        date_time__range=(today_start, today_end),
        status__in=['Pending', 'Continue']
    ).select_related('patient')
    
    # Organize data by gender and status
    male_pending = []
    female_pending = []
    male_continue = []
    female_continue = []
    
    # Process sessions
    for session in pending_sessions:
        if session.status == 'Pending':
            if session.patient.gender == 'Male':
                male_pending.append({
                    'type': 'Session',
                    'id': session.id,
                    'patient_name': session.patient.name,
                    'phone': session.patient.phone_number,
                    'time': session.date_time.strftime('%H:%M')
                })
            else:
                female_pending.append({
                    'type': 'Session',
                    'id': session.id,
                    'patient_name': session.patient.name,
                    'phone': session.patient.phone_number,
                    'time': session.date_time.strftime('%H:%M')
                })
        else:  # Continue
            if session.patient.gender == 'Male':
                male_continue.append({
                    'type': 'Session',
                    'id': session.id,
                    'patient_name': session.patient.name,
                    'phone': session.patient.phone_number,
                    'time': session.date_time.strftime('%H:%M')
                })
            else:
                female_continue.append({
                    'type': 'Session',
                    'id': session.id,
                    'patient_name': session.patient.name,
                    'phone': session.patient.phone_number,
                    'time': session.date_time.strftime('%H:%M')
                })
    
    # Process consultancies
    for consultancy in pending_consultancies:
        if consultancy.status == 'Pending':
            if consultancy.patient.gender == 'Male':
                male_pending.append({
                    'type': 'Consultancy',
                    'id': consultancy.id,
                    'patient_name': consultancy.patient.name,
                    'phone': consultancy.patient.phone_number,
                    'time': consultancy.date_time.strftime('%H:%M')
                })
            else:
                female_pending.append({
                    'type': 'Consultancy',
                    'id': consultancy.id,
                    'patient_name': consultancy.patient.name,
                    'phone': consultancy.patient.phone_number,
                    'time': consultancy.date_time.strftime('%H:%M')
                })
        else:  # Continue
            if consultancy.patient.gender == 'Male':
                male_continue.append({
                    'type': 'Consultancy',
                    'id': consultancy.id,
                    'patient_name': consultancy.patient.name,
                    'phone': consultancy.patient.phone_number,
                    'time': consultancy.date_time.strftime('%H:%M')
                })
            else:
                female_continue.append({
                    'type': 'Consultancy',
                    'id': consultancy.id,
                    'patient_name': consultancy.patient.name,
                    'phone': consultancy.patient.phone_number,
                    'time': consultancy.date_time.strftime('%H:%M')
                })
    
    # Sort all lists by time
    male_pending.sort(key=lambda x: x['time'])
    female_pending.sort(key=lambda x: x['time'])
    male_continue.sort(key=lambda x: x['time'])
    female_continue.sort(key=lambda x: x['time'])
    
    # Prepare context
    context = {
        'male_pending': male_pending,
        'female_pending': female_pending,
        'male_continue': male_continue,
        'female_continue': female_continue,
        'current_date': today.strftime('%B %d, %Y'),
    }
    
    # Render the home page with the context data
    return render(request, "home.html", context)


class RedirectURLMixin:
    next_page = None
    redirect_field_name = REDIRECT_FIELD_NAME
    success_url_allowed_hosts = set()

    def get_success_url(self):
        return self.get_redirect_url() or self.get_default_redirect_url()

    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = self.request.POST.get(
            self.redirect_field_name, self.request.GET.get(self.redirect_field_name)
        )
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ""

    def get_success_url_allowed_hosts(self):
        return {self.request.get_host(), *self.success_url_allowed_hosts}

    def get_default_redirect_url(self):
        """Return the default redirect URL."""
        if self.next_page:
            return resolve_url(self.next_page)
        return "/"


class LoginView(RedirectURLMixin, FormView):
    """
    Display the login form and handle the login action.
    """

    form_class = EmailAuthenticationForm
    authentication_form = None
    template_name = "login.html"
    redirect_authenticated_user = False
    extra_context = None

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and self.request.user.is_authenticated:

            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)

    def get_default_redirect_url(self):
        """Return the default redirect URL."""
        if self.next_page:
            return resolve_url(self.next_page)
        else:
            return resolve_url("/")

    def get_form_class(self):
        return self.authentication_form or self.form_class

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        auth_login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_site = get_current_site(self.request)
        context.update(
            {
                self.redirect_field_name: self.get_redirect_url(),
                "site": current_site,
                "site_name": current_site.name,
                **(self.extra_context or {}),
            }
        )
        return context


class LogoutView(RedirectURLMixin, TemplateView):
    """
    Log out the user and display the 'You are logged out' message.
    """

    http_method_names = ["post", "options"]
    template_name = "home.html"
    extra_context = None

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Logout may be done via POST."""
        auth_logout(request)
        redirect_to = self.get_success_url()
        if redirect_to != request.get_full_path():
            # Redirect to target page once the session has been cleared.
            return HttpResponseRedirect(redirect_to)
        return super().get(request, *args, **kwargs)

    def get_default_redirect_url(self):
        """Return the default redirect URL."""
        if self.next_page:
            return resolve_url(self.next_page)
        else:
            return resolve_url("/")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_site = get_current_site(self.request)
        context.update(
            {
                "site": current_site,
                "site_name": current_site.name,
                "title": _("Logged out"),
                "subtitle": None,
                **(self.extra_context or {}),
            }
        )
        return context



class OrganizationCreateView(LoginRequiredMixin,CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organization_create.html'
    success_url = reverse_lazy('accounts:create_organization') 
    login_url = reverse_lazy('accounts:login') 


class UserProfileCreateView(LoginRequiredMixin,CreateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'user_profile_create.html' 
    success_url = reverse_lazy('accounts:create_user')  
    login_url = reverse_lazy('accounts:login') 




User = get_user_model()

class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'organization_list.html'
    context_object_name = 'organizations'
    login_url = reverse_lazy('accounts:login')
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Organization.objects.all().order_by('name')
        query = self.request.GET.get('q')
        
        if query:
            queryset = queryset.filter(name__icontains=query)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context

class OrganizationUsersView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organization_users.html'
    context_object_name = 'organization'
    login_url = reverse_lazy('accounts:login')
    pk_url_kwarg = 'organization_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object()
        
        # Get all users associated with this organization
        # Assuming User model has a ForeignKey to Organization called 'organization'
        users = User.objects.filter(organization=organization).order_by('username')
        
        # Apply search filter if provided
        search_query = self.request.GET.get('user_search', '')
        if search_query:
            users = users.filter(
                username__icontains=search_query
            ) | users.filter(
                first_name__icontains=search_query
            ) | users.filter(
                last_name__icontains=search_query
            ) | users.filter(
                email__icontains=search_query
            )
        
        # Get role filter if provided
        role_filter = self.request.GET.get('role', '')
        if role_filter:
            users = users.filter(role=role_filter)
        
        # Get status filter if provided
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            is_active = status_filter == 'active'
            users = users.filter(is_active=is_active)
        
        # Get distinct roles for filter dropdown
        roles = User.objects.filter(organization=organization).values_list('role', flat=True).distinct()
        
        context.update({
            'users': users,
            'user_count': users.count(),
            'search_query': search_query,
            'role_filter': role_filter,
            'status_filter': status_filter,
            'available_roles': roles,
        })
        
        return context



class EditOrganizationView(LoginRequiredMixin, UpdateView):
    model = Organization
    template_name = 'edit_organization.html'
    fields = ['name', 'location']
    pk_url_kwarg = 'organization_id'
    login_url = reverse_lazy('accounts:login')
    
    def get_success_url(self):
        return reverse('accounts:users', kwargs={'organization_id': self.object.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.object
        return context

class DeleteOrganizationView(LoginRequiredMixin, DeleteView):
    model = Organization
    template_name = 'delete_organization.html'
    pk_url_kwarg = 'organization_id'
    success_url = reverse_lazy('accounts:list')
    login_url = reverse_lazy('accounts:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Count users that will be affected by this deletion
        user_count = User.objects.filter(organization=self.object).count()
        context['user_count'] = user_count
        return context
    
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
    


class EditUserView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'edit_user.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']
    pk_url_kwarg = 'user_id'
    login_url = reverse_lazy('accounts:login')
    
    def get_success_url(self):
        return reverse('accounts:users', kwargs={'organization_id': self.object.organization.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_obj'] = self.object  # Using user_obj to avoid conflict with user template variable
        context['organization'] = self.object.organization
        return context

class DeleteUserView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'delete_user.html'
    pk_url_kwarg = 'user_id'
    login_url = reverse_lazy('accounts:login')
    
    def get_success_url(self):
        return reverse('accounts:users', kwargs={'organization_id': self.object.organization.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_obj'] = self.object  # Using user_obj to avoid conflict with user template variable
        context['organization'] = self.object.organization
        return context
    
    def delete(self, request, *args, **kwargs):
        organization_id = self.get_object().organization.id
        return super().delete(request, *args, **kwargs)
