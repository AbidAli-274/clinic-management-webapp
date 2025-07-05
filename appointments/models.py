from django.db import models

from accounts.models import UserProfile
from patients.models import Patient


class Consultancy(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Continue", "Continue"),
        ("ReceptionistReview", "Receptionist Review"),
        ("Completed", "Completed"),
        ("PendingDiscount", "Pending Discount Approval"),
        ("Rejected", "Rejected"),
        ("SessionEnded", "Session Ended"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    chief_complaint = models.TextField()
    date_time = models.DateTimeField()
    referred_doctor = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "doctor"},
    )
    consultancy_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=1000.00
    )
    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, null=True, blank=True
    )
    number_of_sessions = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
    )
    room = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "room"},
        related_name="consultancies_as_room",
    )

    def __str__(self):
        return f"{self.patient.name} - {self.date_time}"

    class Meta:
        verbose_name = "Consultancy"
        verbose_name_plural = "Consultancies"


class Session(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Continue", "Continue"),
        ("Completed", "Completed"),
        ("PendingDiscount", "Pending Discount Approval"),
        ("Rejected", "Rejected"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={"role": "doctor"},
    )
    consultancy = models.ForeignKey(Consultancy, on_delete=models.CASCADE)
    session_fee = models.DecimalField(max_digits=10, decimal_places=2, default=2500.00)
    further_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, null=True, blank=True
    )
    feedback = models.TextField(blank=True, null=True)
    date_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    room = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "room"},
        related_name="sessions_as_room",
    )

    def __str__(self):
        return f"Session {self.id} - {self.patient.name}"

    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
        unique_together = ['patient', 'consultancy', 'date_time']
