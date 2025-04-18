from django.db import models
from accounts.models import UserProfile
from patients.models import Patient


class Consultancy(models.Model):
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Continue', 'Continue'),
        ('Completed', 'Completed'),
        ('PendingDiscount', 'Pending Discount Approval'),
        ('Rejected', 'Rejected'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    chief_complaint = models.TextField()
    date_time = models.DateTimeField()
    referred_doctor = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'doctor'}
    )
    consultancy_fee = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    number_of_sessions = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='Pending',
    )

    def __str__(self):
        return f"{self.patient.name} - {self.patient.phone_number}"

    class Meta:
        verbose_name = "Consultancy"
        verbose_name_plural = "Consultancies"


class Session(models.Model):
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Continue', 'Continue'),
        ('Completed', 'Completed'),
        ('PendingDiscount', 'Pending Discount Approval'),
        ('Rejected', 'Rejected'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'doctor'}
    )
    consultancy = models.ForeignKey(Consultancy, on_delete=models.CASCADE)
    session_fee = models.DecimalField(max_digits=10, decimal_places=2)
    further_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    feedback = models.TextField(blank=True, null=True)
    date_time = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='Pending',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} - {self.patient.name}"

    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"

