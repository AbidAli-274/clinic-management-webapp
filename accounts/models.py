from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class UserProfile(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("s_admin", "Super Admin"),
        ("doctor", "Doctor"),
        ("receptionist", "Receptionist"),
        ("room", "Room"),
        ("waiting_screen", "Waiting Screen"),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True
    )
    age = models.PositiveIntegerField(null=True, blank=True)
    contact = models.CharField(max_length=15, unique=True)
    gender = models.CharField(
        max_length=10,
        choices=[("Male", "Male"), ("Female", "Female")],
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
