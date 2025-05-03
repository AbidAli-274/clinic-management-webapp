from django import forms
from django_select2.forms import ModelSelect2Widget

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

    # Session Fee field
    session_fee = forms.DecimalField(
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
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Number of Sessions",
            }
        ),
        label="Number of Sessions",
    )
