from django import forms
from .models import Patient

class PatientForm(forms.ModelForm):
    name = forms.CharField(
        label="Name",
        widget=forms.TextInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Full Name",
            }
        ),
    )
    
    phone_number = forms.CharField(
        label="Phone Number",
        widget=forms.TextInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Phone Number",
            }
        ),
    )

    city = forms.CharField(
        label="City",
        widget=forms.TextInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "City",
            }
        ),
    )
    
    gender = forms.ChoiceField(
        label="Gender",
        choices=[('Male', 'Male'), ('Female', 'Female')],
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
    )

    class Meta:
        model = Patient
        fields = ['name', 'phone_number', 'city', 'gender']
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        if not phone_number.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        if len(phone_number) != 11:
            raise forms.ValidationError("Phone number must be 11 digits long.")
        return phone_number
