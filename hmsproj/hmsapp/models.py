from django.db import models
from django.contrib.auth.models import User, Group
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.signals import post_migrate
from django.apps import apps
from datetime import date, datetime, timedelta
from hmsapp.utils.google_calendar import get_google_calendar_service, create_calendar_event, delete_calendar_event
from django.db.models import Count, Avg, Sum, F
from django.db.models.functions import TruncMonth, TruncYear, ExtractMonth
from decimal import Decimal
from dateutil.relativedelta import relativedelta

# Phone number validator
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

class DoctorProfile(models.Model):
    """Profile for doctors"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialty = models.ForeignKey('Specialty', on_delete=models.SET_NULL, null=True)
    license_number = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=15, validators=[phone_regex])
    address = models.TextField(blank=True)
    doctor_id = models.CharField(max_length=6, unique=True, blank=True)
    profile_picture = models.ImageField(
        upload_to='doctors/profile_pics/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    google_calendar_enabled = models.BooleanField(default=False)
    google_calendar_credentials = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.doctor_id:
            last_doctor = DoctorProfile.objects.all().order_by('id').last()
            if last_doctor:
                last_id = int(last_doctor.doctor_id[1:])
                new_id = last_id + 1
            else:
                new_id = 1
            self.doctor_id = f'D{new_id:05}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

    def is_available(self, appointment_datetime):
        """Check if the doctor is available at the given appointment datetime."""
        # Get the day of the week (0=Monday, 6=Sunday)
        day_of_week = appointment_datetime.weekday()
        
        # Get the time from the appointment datetime
        appointment_time = appointment_datetime.time()

        # Check if there is an availability slot for this doctor on the specified day
        availability_slots = self.availabilities.filter(day_of_week=day_of_week, is_available=True)

        for slot in availability_slots:
            if slot.start_time <= appointment_time <= slot.end_time:
                return True  # Doctor is available during this time slot

        return False  # No available slot found

class StaffProfile(models.Model):
    """Profile for staff members"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, validators=[phone_regex])
    address = models.TextField(blank=True)
    staff_id = models.CharField(max_length=7, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.staff_id:
            last_staff = StaffProfile.objects.all().order_by('id').last()
            if last_staff:
                last_id = int(last_staff.staff_id[1:])
                new_id = last_id + 1
            else:
                new_id = 1
            self.staff_id = f'S{new_id:06}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff_id} - {self.user.get_full_name()}"

# Keep other models but update Doctor references
class DoctorAvailability(models.Model):
    """Model to track doctor's available time slots"""
    
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Doctor Availabilities"
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.get_day_of_week_display()}"

class Patient(models.Model):
    """Patient model representing hospital patients"""
    
    BLOOD_GROUPS = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]
    
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Changed to OneToOneField
    patient_name = models.CharField(max_length=100)  # Removed blank=True
    date_of_birth = models.DateField()
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS)  # Added choices
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)  # Added choices
    nationality = models.CharField(max_length=50)
    referred_by = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, validators=[phone_regex])
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=15, validators=[phone_regex])
    medical_history = models.TextField(blank=True)
    drug_allergies = models.TextField(blank=True)
    food_allergies = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    patient_id = models.CharField(max_length=9, unique=True, blank=True)
    profile_picture = models.ImageField(
        upload_to='patients/profile_pics/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    age = models.IntegerField(null=True, blank=True)

    @property
    def calculated_age(self):
        if self.date_of_birth:
            today = date.today()
            return relativedelta(today, self.date_of_birth).years
        return 0

    def save(self, *args, **kwargs):
        self.age = self.calculated_age
        if not self.patient_id:
            last_patient = Patient.objects.all().order_by('id').last()
            if last_patient:
                last_id = int(last_patient.patient_id[1:])
                new_id = last_id + 1
            else:
                new_id = 1
            self.patient_id = f'P{new_id:08}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_id} - {self.patient_name}"

class Appointment(models.Model):
    """Model for appointments"""
    APPOINTMENT_STATUS = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]
    
    appointment_id = models.CharField(max_length=10, unique=True, null=True, blank=True, default=None)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(max_length=20, choices=APPOINTMENT_STATUS, default='SCHEDULED')
    notes = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, validators=[phone_regex], null=True, blank=True)
    medical_records = models.FileField(upload_to='medical_records/', null=True, blank=True)
    google_calendar_event_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_time']

    def __str__(self):
        return f"{self.patient} with {self.doctor} on {self.appointment_date}"

    def save(self, *args, **kwargs):
        if not self.appointment_id:
            last_appointment = Appointment.objects.order_by('-id').first()
            if last_appointment and last_appointment.appointment_id:
                last_id = int(last_appointment.appointment_id[1:])
                new_id = last_id + 1
            else:
                new_id = 1
            self.appointment_id = f'A{new_id:09d}'
        super().save(*args, **kwargs)

    @property
    def appointment_datetime(self):
        return datetime.combine(self.appointment_date, self.appointment_time)

    @property
    def duration(self):
        return timedelta(minutes=30)  # Default 30-minute appointments

class Treatment(models.Model):
    """Model to track patient treatments"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='treatments')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='treatments')
    # Make appointment optional
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, null=True, blank=True)
    chief_complaint = models.TextField()
    examination_findings = models.TextField()
    drug_history = models.TextField(blank=True)
    diagnosis = models.TextField()
    prescription = models.TextField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Treatment for {self.patient} by {self.doctor}"

class Bill(models.Model):
    """Model to track patient bills and payments"""
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('OVERDUE', 'Overdue'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='bills')
    treatment = models.OneToOneField(Treatment, on_delete=models.CASCADE, related_name='bill')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    due_date = models.DateField()
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.paid_amount > self.amount:
            raise ValidationError('Paid amount cannot be greater than total amount')

    def __str__(self):
        return f"Bill #{self.id} for {self.patient}"

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        return self.amount - self.paid_amount

    @property
    def payments(self):
        """Return all payments associated with this bill"""
        return self.payment_set.all().order_by('-payment_date')

    @property
    def is_overdue(self):
        return date.today() > self.due_date and self.payment_status != 'PAID'

class MedicalRecord(models.Model):
    """Model to store patient medical records and documents"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    record_date = models.DateField()
    description = models.TextField()
    document = models.FileField(
        upload_to='patients/medical_records/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-record_date']

    def __str__(self):
        return f"{self.patient.patient_name}'s record - {self.record_date}"

class Specialty(models.Model):
    """Medical specialties for doctors"""
    
    specialty_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Specialties"

    def __str__(self):
        return self.specialty_name

@receiver(post_migrate)
def create_groups(sender, **kwargs):
    Group = apps.get_model('auth', 'Group')
    if sender.name == 'hmsapp':
        for group_name in ['Administrators', 'Doctors', 'Staff']:
            Group.objects.get_or_create(name=group_name)

# Add to StaffProfile model
@receiver(post_save, sender=User)
def create_staff_profile(sender, instance, created, **kwargs):
    if created and instance.groups.filter(name='Staff').exists():
        StaffProfile.objects.get_or_create(
            user=instance,
            defaults={
                'department': 'Not Specified',
                'designation': 'Not Specified',
                'phone_number': 'Not Specified',
                'address': ''
            }
        )
@receiver(post_save, sender=Appointment)
def sync_appointment_to_calendar(sender, instance, created, **kwargs):
    """Sync appointment to Google Calendar when created or updated"""
    if instance.doctor.google_calendar_enabled and instance.doctor.google_calendar_credentials:
        service = get_google_calendar_service(instance.doctor.google_calendar_credentials)
        
        # Delete existing event if it exists
        if instance.google_calendar_event_id:
            delete_calendar_event(service, instance.google_calendar_event_id)
        
        # Create new event if appointment is not cancelled
        if instance.status != 'CANCELLED':
            event_id = create_calendar_event(service, instance)
            if event_id:
                # Update the appointment with the new event ID without triggering the signal again
                Appointment.objects.filter(pk=instance.pk).update(google_calendar_event_id=event_id)

class UserActivity(models.Model):
    """Model to track user activities"""
    
    ACTIVITY_TYPES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    activity_description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'User Activities'

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp}"

class LoginActivity(models.Model):
    """Model to track user login activities"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    login_datetime = models.DateTimeField(auto_now_add=True)
    logout_datetime = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    class Meta:
        ordering = ['-login_datetime']
        verbose_name_plural = 'Login Activities'

    def __str__(self):
        return f"{self.user.username} - {self.login_datetime}"

class ReportConfiguration(models.Model):
    """Model to store customizable report configurations"""
    
    REPORT_TYPES = [
        ('PATIENT_DEMOGRAPHICS', 'Patient Demographics'),
        ('REVENUE_ANALYSIS', 'Revenue Analysis'),
        ('APPOINTMENT_TRENDS', 'Appointment Trends'),
        ('SERVICE_UTILIZATION', 'Service Utilization'),
        ('DOCTOR_PERFORMANCE', 'Doctor Performance'),
    ]
    
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]
    
    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    filters = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"

# Add this new model after the Bill model
class Payment(models.Model):
    """Model to track individual payments for bills"""
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('INSURANCE', 'Insurance'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('UPI', 'UPI Payment'),
    ]
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payment_set')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of ₹{self.amount} for Bill #{self.bill.id}"

    def save(self, *args, **kwargs):
        # Update the bill's paid amount when a payment is saved
        super().save(*args, **kwargs)
        
        # Update bill's paid amount and status
        bill = self.bill
        total_paid = bill.payment_set.aggregate(total=models.Sum('amount'))['total'] or 0
        bill.paid_amount = total_paid
        
        if total_paid >= bill.amount:
            bill.payment_status = 'PAID'
        elif total_paid > 0:
            bill.payment_status = 'PARTIALLY_PAID'
        elif bill.due_date < date.today():
            bill.payment_status = 'OVERDUE'
        else:
            bill.payment_status = 'PENDING'
        
        bill.save()

def calculate_age(dob):
    """Calculate age from date of birth"""
    today = date.today()
    return relativedelta(today, dob).years
