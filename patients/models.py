from django.db import models
from accounts.models import Organization


class Patient(models.Model):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    city = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])
    created_at = models.DateTimeField(auto_now_add=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)


    def __str__(self):
        return f'{self.name} - {self.phone_number}'

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"