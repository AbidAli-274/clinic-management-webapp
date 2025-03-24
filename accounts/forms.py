from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth import get_user_model
from accounts.models import Organization, UserProfile
from django.core.exceptions import ValidationError


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email Address",
        widget=forms.TextInput(
            attrs={
                "class": "pl-10 w-full px-4 py-3 border border-gray-300 rounded-lg  focus:ring-blue-500 focus:border-blue-500 transition-all duration-300",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "pl-10 w-full px-4 py-3 border border-gray-300 rounded-lg  focus:ring-blue-500 focus:border-blue-500 transition-all duration-300",
            }
        ),
    )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        try:
            user = get_user_model().objects.get(email=username)
        except get_user_model().DoesNotExist:
            raise forms.ValidationError("User with this email does not exist.")
        return user


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'location']
    
    name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "pl-10 w-full px-4 py-3 border border-gray-300 rounded-lg  focus:ring-blue-500 focus:border-blue-500 transition-all duration-300",
            }
        ),
        label="Organization Name"
    )

    location = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "pl-10 w-full px-4 py-3 border border-gray-300 rounded-lg  focus:ring-blue-500 focus:border-blue-500 transition-all duration-300",
            }
        ),
        label="Location"
    )



class UserProfileForm(UserCreationForm):
    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'age', 'contact', 'gender', 'role', 'organization']

    # Username field (provided by UserCreationForm)
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Username"
            }
        ),
        label="Username"
    )

    # Email field (provided by UserCreationForm)
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Email Address"
            }
        ),
        label="Email"
    )

    # Age field
    age = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Age"
            }
        ),
        required=False,
        label="Age"
    )

    # Contact field
    contact = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Contact Number"
            }
        ),
        label="Contact"
    )

    # Gender field
    gender = forms.ChoiceField(
        choices=[('Male', 'Male'), ('Female', 'Female')],
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        required=False,
        label="Gender"
    )

    # Role field
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Role"
    )

    # Organization field
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
            }
        ),
        label="Organization"
    )

    # Password field 1 (provided by UserCreationForm)
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Password"
            }
        ),
        label="Password",
    )

    # Password field 2 (provided by UserCreationForm)
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none  focus:ring-blue-500",
                "placeholder": "Confirm Password"
            }
        ),
        label="Confirm Password",
    )

    def __init__(self, *args, **kwargs):
        # Initialize the form
        super().__init__(*args, **kwargs)

        # Check if the role is 'Doctor' and make the password fields not required
        if 'role' in self.data and self.data['role'] == 'doctor':
            self.fields['password1'].required = False
            self.fields['password2'].required = False
        elif 'role' in self.initial and self.initial['role'] == 'doctor':
            self.fields['password1'].required = False
            self.fields['password2'].required = False

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')

        # If the role is 'doctor', set password fields to default password
        if role == 'doctor':
            # Don't set passwords if they are not provided
            if not cleaned_data.get('password1') or not cleaned_data.get('password2'):
                cleaned_data['password1'] = 'defaultpassword123'
                cleaned_data['password2'] = 'defaultpassword123'

            # Ensure passwords match
            if cleaned_data['password1'] != cleaned_data['password2']:
                raise ValidationError('Passwords do not match.')

        return cleaned_data