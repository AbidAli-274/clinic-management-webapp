from django import forms
from django_select2.forms import ModelSelect2Widget
from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.models import UserProfile
from patients.models import Patient

from .models import Consultancy, Session


class ConsultancyForm(forms.ModelForm):
    class Meta:
        model = Consultancy
        fields = [
            "patient",
            "chief_complaint",
            "consultancy_fee",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # Extract the user from kwargs
        super().__init__(*args, **kwargs)
        if user and user.organization:
            # Filter patients by the user's organization
            self.fields["patient"].queryset = Patient.objects.filter(
                organization=user.organization
            )
        else:
            self.fields["patient"].queryset = (
                Patient.objects.none()
            )  # No patients if no organization

    # Customizing widgets to make the form look nicer
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.none(),  # Default queryset
        widget=ModelSelect2Widget(
            model=Patient,
            search_fields=["phone_number__icontains", "name__icontains"],
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            },
        ),
        label="Patient",
    )

    chief_complaint = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Chief Complaint",
                "rows": 4,
            }
        ),
        label="Chief Complaint",
    )

    consultancy_fee = forms.DecimalField(
        initial=1000.00,
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Consultancy Fee",
            }
        ),
        label="Consultancy Fee",
    )


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            "patient",
            "doctor",
            "consultancy",
            "session_fee",
            "further_discount",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # Extract the user from kwargs
        super().__init__(*args, **kwargs)
        if user and user.organization:
            # Filter patients by the user's organization
            self.fields["patient"].queryset = Patient.objects.filter(
                organization=user.organization
            )
            # Filter doctors by the user's organization
            self.fields["doctor"].queryset = UserProfile.objects.filter(
                organization=user.organization, role="doctor"
            )
        else:
            self.fields["patient"].queryset = (
                Patient.objects.none()
            )  # No patients if no organization
            self.fields["doctor"].queryset = (
                UserProfile.objects.none()
            )  # No doctors if no organization

    def clean(self):
        cleaned_data = super().clean()
        patient = cleaned_data.get('patient')
        consultancy = cleaned_data.get('consultancy')
        
        if patient and consultancy:
            # Check if a session already exists for this patient and consultancy
            # within the last 5 seconds (to prevent duplicates from rapid submissions)
            current_time = timezone.now()
            five_seconds_ago = current_time - timezone.timedelta(seconds=5)
            
            existing_session = Session.objects.filter(
                patient=patient,
                consultancy=consultancy,
                date_time__gte=five_seconds_ago
            ).first()
            
            if existing_session:
                raise ValidationError(
                    f"A session for {patient.name} under this consultancy was created recently. "
                    "Please wait a moment before creating another session."
                )
        
        return cleaned_data

    # Patient field
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.none(),  # Default queryset
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Patient",
    )

    # Doctor field (only show doctors)
    doctor = forms.ModelChoiceField(
        queryset=UserProfile.objects.none(),  # Default queryset
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "disabled": "true",
            }
        ),
        label="Doctor",
    )

    # Consultancy field
    consultancy = forms.ModelChoiceField(
        queryset=Consultancy.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Consultancy",
    )

    # Consultancy Discount field (non-editable)
    consultancy_discount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-blue-500",
                "readonly": "readonly",
                "placeholder": "Consultancy Discount",
            }
        ),
        label="Consultancy Discount",
    )

    # Session Fee field
    session_fee = forms.DecimalField(
        initial=2500.00,
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Session Fee",
            }
        ),
        label="Session Fee",
    )

    # Further Discount field
    further_discount = forms.DecimalField(
        initial=0.00,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-blue-500",
                "placeholder": "Further Discount",
            }
        ),
        label="Further Discount",
    )


class ReceptionistConsultancyForm(forms.ModelForm):
    class Meta:
        model = Consultancy
        fields = [
            "referred_doctor",
            "discount",
            "number_of_sessions",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and user.organization:
            # only doctors in this org
            self.fields["referred_doctor"].queryset = UserProfile.objects.filter(
                organization=user.organization, role="doctor"
            )
        else:
            self.fields["referred_doctor"].queryset = UserProfile.objects.none()

    referred_doctor = forms.ModelChoiceField(
        queryset=UserProfile.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Referred Doctor",
    )

    discount = forms.DecimalField(
        initial=0.00,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Discount",
            }
        ),
        label="Discount",
    )

    number_of_sessions = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Number of Sessions",
            }
        ),
        label="Number of Sessions",
    )
