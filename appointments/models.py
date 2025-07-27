from django.db import models

from accounts.models import UserProfile
from patients.models import Patient


class RecordLog(models.Model):
    """Model to store transaction records for efficient reporting"""

    RECORD_TYPE_CHOICES = [
        ("consultancy", "Consultancy"),
        ("session", "Session"),
        ("advance", "Advance"),
    ]

    # Basic record information
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    date_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Patient information
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    patient_name = models.CharField(max_length=255)
    patient_phone = models.CharField(max_length=15)
    patient_gender = models.CharField(max_length=10)

    # Doctor information
    doctor = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "doctor"},
    )
    doctor_name = models.CharField(max_length=255, blank=True)

    # Financial information
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    further_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Status and additional information
    status = models.CharField(max_length=20)
    feedback = models.TextField(blank=True, null=True)
    feedback_type = models.CharField(max_length=20, blank=True, null=True)

    # Related models (for reference)
    consultancy = models.ForeignKey(
        "Consultancy", on_delete=models.CASCADE, null=True, blank=True
    )
    session = models.ForeignKey(
        "Session", on_delete=models.CASCADE, null=True, blank=True
    )

    # Organization information
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, null=True, blank=True
    )

    # Additional fields for consultancy
    number_of_sessions = models.PositiveIntegerField(null=True, blank=True)
    chief_complaint = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Record Log"
        verbose_name_plural = "Record Logs"
        indexes = [
            models.Index(fields=["date_time"]),
            models.Index(fields=["record_type"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["doctor"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.record_type.title()} - {self.patient_name} - {self.date_time.strftime('%Y-%m-%d %H:%M')}"


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
    paid_sessions = models.PositiveIntegerField(null=True, blank=True, default=0)
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
        unique_together = ["patient", "consultancy", "date_time"]
