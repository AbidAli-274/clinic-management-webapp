from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth import get_user_model


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email Address",
        widget=forms.TextInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "Email address",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "border border-gray-300 rounded-md px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-red-500",
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
