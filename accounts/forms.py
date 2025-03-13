from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth import get_user_model

from accounts.models import Organization, UserProfile


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email Address",
        widget=forms.TextInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Email address",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Password",
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
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Organization Name",
            }
        ),
        label="Organization Name"
    )

    location = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Location",
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
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Username"
            }
        ),
        label="Username"
    )

    # Email field (provided by UserCreationForm)
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Email Address"
            }
        ),
        label="Email"
    )

    # Age field
    age = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
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
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
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
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
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
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
            }
        ),
        label="Role"
    )

    # Organization field
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
            }
        ),
        required=False,
        label="Organization"
    )

    # Password field 1 (provided by UserCreationForm)
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Password"
            }
        ),
        label="Password"
    )

    # Password field 2 (provided by UserCreationForm)
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Confirm Password"
            }
        ),
        label="Confirm Password"
    )
