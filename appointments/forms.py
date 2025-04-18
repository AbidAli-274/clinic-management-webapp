from django import forms
from .models import Consultancy,Session
from patients.models import Patient
from accounts.models import UserProfile
from django_select2.forms import ModelSelect2Widget



class ConsultancyForm(forms.ModelForm):
    class Meta:
        model = Consultancy
        fields = ['patient', 'chief_complaint', 'referred_doctor', 'consultancy_fee', 'discount', 'number_of_sessions']
    
    # Customizing widgets to make the form look nicer
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all(),
        widget=ModelSelect2Widget(
            model=Patient, 
            search_fields=['phone_number__icontains','name__icontains'],
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Patient"
    )

    chief_complaint = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Chief Complaint",
                "rows": 4,
            }
        ),
        label="Chief Complaint"
    )

    referred_doctor = forms.ModelChoiceField(
        queryset=UserProfile.objects.filter(role='doctor'),
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Referred Doctor"
    )

    consultancy_fee = forms.DecimalField(
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Consultancy Fee",
            }
        ),
        label="Consultancy Fee"
    )

    discount = forms.DecimalField(
        initial=0.00,
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Discount",
            }
        ),
        label="Discount"
    )

    number_of_sessions = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Number of Sessions",
            }
        ),
        label="Number of Sessions"
    )



class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['patient', 'doctor', 'consultancy', 'session_fee', 'further_discount', 'feedback']
    
    # Patient field
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Patient"
    )

    # Doctor field (only show doctors)
    doctor = forms.ModelChoiceField(
        queryset=UserProfile.objects.filter(role='doctor'),
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Doctor"
    )

    # Consultancy field
    consultancy = forms.ModelChoiceField(
        queryset=Consultancy.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Consultancy"
    )

    # Session Fee field
    session_fee = forms.DecimalField(
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Session Fee",
            }
        ),
        label="Session Fee"
    )
    
    # Further Discount field
    further_discount = forms.DecimalField(
        initial=0.00,
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-blue-500",
                "placeholder": "Further Discount",
            }
        ),
        label="Further Discount"
    )

    FEEDBACK_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('mixed', 'Mixed'),
    ]

    feedback = forms.ChoiceField(
        choices=FEEDBACK_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-blue-500",
            }
        ),
        required=False,
        label="Feedback"
    )
