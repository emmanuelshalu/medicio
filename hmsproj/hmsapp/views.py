from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from datetime import date, datetime, timedelta, time
from .models import *
from .decorators import admin_required, doctor_required, staff_required, track_activity
from decimal import Decimal
from django.core.files.storage import FileSystemStorage
from google_auth_oauthlib.flow import Flow
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import datetime
from django.contrib.auth import signals
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Sum, F
from django.db.models.functions import TruncMonth, TruncYear, ExtractMonth
from django.core.serializers.json import DjangoJSONEncoder
import json
from collections import defaultdict
import qrcode
import base64
from io import BytesIO
from dateutil.relativedelta import relativedelta




def get_doctor_availability(doctor, day_of_week):
    """
    Get doctor's availability for a given day. Returns default availability if none is set.
    Default availability is Mon-Sat: 9-12 and 15-17
    Returns a list of tuples containing (start_time, end_time)
    """
    # Check if custom availability exists
    custom_availability = DoctorAvailability.objects.filter(
        doctor=doctor,
        day_of_week=day_of_week,
        is_available=True
    )
    
    if custom_availability.exists():
        return [(slot.start_time, slot.end_time) for slot in custom_availability]
    
    # Return default availability for Monday-Saturday
    if day_of_week < 6:  # 0-5 represents Monday-Saturday
        return [
            (time(9, 0), time(12, 0)),   # Morning slot: 9 AM - 12 PM
            (time(15, 0), time(17, 0))   # Evening slot: 3 PM - 5 PM
        ]
    
    # Sunday (day_of_week = 6) has no availability by default
    return []

def home(request):
    doctors = DoctorProfile.objects.all()
    specialties = Specialty.objects.all()
    context = {
        'doctors': doctors,
        'specialties': specialties,
    }
    return render(request, 'home.html', context)

def calculate_age(dob):
    """Calculate age from date of birth"""
    today = date.today()
    return relativedelta(today, dob).years

def book_appointment(request):
    if request.method == 'POST':
        try:
            # Get mandatory form data
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            date_of_birth = request.POST.get('date_of_birth')
            gender = request.POST.get('gender')
            phone_number = request.POST.get('phone_number')
            doctor_id = request.POST.get('doctor')
            appointment_date = request.POST.get('appointment_date')
            appointment_time = request.POST.get('appointment_time')
            reason = request.POST.get('reason')
            notes = request.POST.get('notes', '')
            status = request.POST.get('status', 'SCHEDULED')

            # Validate mandatory fields
            if not all([first_name, last_name, date_of_birth, gender, phone_number]):
                messages.error(request, 'Please fill all mandatory fields')
                return redirect('book_appointment')

            # Convert date_of_birth string to date object
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            
            # Calculate age
            age = calculate_age(dob)

            # Create user for patient
            username = f"patient_{phone_number}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name
                }
            )

            # Get or create patient with mandatory fields
            patient_name = f"{first_name} {last_name}"
            patient, created = Patient.objects.get_or_create(
                phone_number=phone_number,
                defaults={
                    'user': user,
                    'patient_name': patient_name,
                    'date_of_birth': dob,
                    'age': age,  # Add calculated age
                    'gender': gender,
                    'nationality': 'Not Specified',
                    'emergency_contact_name': patient_name,
                    'emergency_contact_phone': phone_number
                }
            )

            # Update patient information if they already exist
            if not created:
                patient.patient_name = patient_name
                patient.date_of_birth = dob
                patient.age = age  # Update age
                patient.gender = gender
                patient.save()

            # Create appointment
            appointment_datetime = timezone.make_aware(datetime.combine(
                datetime.strptime(appointment_date, '%Y-%m-%d').date(),
                datetime.strptime(appointment_time, '%H:%M').time()
            ))
            
            appointment = Appointment.objects.create(
                patient=patient,
                doctor_id=doctor_id,
                phone_number=phone_number,
                appointment_date=appointment_datetime.date(),
                appointment_time=appointment_datetime.time(),
                reason=reason,
                notes=notes,
                status=status
            )

            # Handle medical records file upload
            if 'medical_records' in request.FILES:
                medical_file = request.FILES['medical_records']
                medical_record = MedicalRecord.objects.create(
                    patient=patient,
                    record_date=timezone.now().date(),
                    description=f"Medical records uploaded during appointment booking - {reason}",
                    document=medical_file
                )
                appointment.medical_records = medical_file
                appointment.save()

            messages.success(request, 'Appointment booked successfully!')
            return redirect('home')

        except Exception as e:
            print(f"Error details: {str(e)}")
            messages.error(request, f'Error booking appointment: {str(e)}')
            return redirect('home')

    # If GET request, render the form
    doctors = DoctorProfile.objects.all()
    context = {
        'doctors': doctors,
        'gender_choices': Patient.GENDER_CHOICES,  # Add gender choices to context
        'min_date': date(1900, 1, 1).isoformat(),  # Minimum allowed date
        'max_date': date.today().isoformat(),  # Maximum allowed date (today)
    }
    return render(request, 'shared/manage_appointments.html', context)

def get_doctors(request, specialty_id):
    doctors = DoctorProfile.objects.filter(specialty_id=specialty_id, is_active=True)
    data = [{'id': doctor.id, 'doc_name': doctor.doc_name} for doctor in doctors]
    return JsonResponse(data, safe=False)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Debug: Print all available groups
            all_groups = Group.objects.all()
            print(f"Available groups: {[g.name for g in all_groups]}")
            
            # Debug: Print user's groups
            user_groups = user.groups.all()
            print(f"User's groups: {[g.name for g in user_groups]}")
            
            if user.groups.filter(name='Staff').exists():
                return redirect('staff_dashboard')
            elif user.groups.filter(name='Administrators').exists():
                return redirect('admin_dashboard')
            elif user.groups.filter(name='Doctors').exists():
                return redirect('doctor_dashboard')
            
            # If no group is assigned, assign to Staff group
            staff_group, created = Group.objects.get_or_create(name='Staff')
            user.groups.add(staff_group)
            
            # Create StaffProfile if it doesn't exist
            StaffProfile.objects.get_or_create(
                user=user,
                defaults={
                    'department': 'General',
                    'designation': 'Staff Member',
                    'phone_number': 'Not Specified',
                    'address': ''
                }
            )
            
            return redirect('staff_dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

def is_super_admin(user):
    return user.is_authenticated and user.is_superuser

def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or 
        user.groups.filter(name='Administrators').exists()
    )

def is_doctor(user):
    return user.is_authenticated and user.groups.filter(name='Doctors').exists()

def is_staff(user):
    return user.is_authenticated and user.groups.filter(name='Staff').exists()

@user_passes_test(is_super_admin)
def manage_admins(request):
    admin_group = Group.objects.get(name='Administrators')
    admin_users = User.objects.filter(groups=admin_group)
    return render(request, 'admin/manage_admins.html', {'admin_users': admin_users})

@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.exclude(
        groups__name__in=['Administrators']
    ).exclude(is_superuser=True)
    return render(request, 'admin/manage_users.html', {'users': users})

@login_required
@admin_required
def admin_dashboard(request):
    today = date.today()
    pending_bills = Bill.objects.filter(
        payment_status__in=['UNPAID', 'PARTIALLY_PAID']
    ).count()

    context = {
        'doctor_count': DoctorProfile.objects.count(),
        'patient_count': Patient.objects.count(),
        'todays_appointments': Appointment.objects.filter(appointment_date=today).count(),
        'pending_bills': pending_bills,
        'recent_appointments': Appointment.objects.order_by('-appointment_date')[:5],
    }
    return render(request, 'hosp_admin/admin_dashboard.html', context)

@login_required
@doctor_required
def doctor_dashboard(request):
    doctor = DoctorProfile.objects.get(user=request.user)
    context = {
        'doctor': doctor,
        'upcoming_appointments': Appointment.objects.filter(
            doctor=doctor,
            appointment_date__gte=date.today()
        ).order_by('appointment_date', 'appointment_time')
    }
    return render(request, 'doctor/doc_dashboard.html', context)

@user_passes_test(is_doctor)
def doctor_profile(request):
    doctor = get_object_or_404(DoctorProfile, user=request.user)
    if request.method == 'POST':
        if 'update_picture' in request.POST and request.FILES.get('profile_picture'):
            doctor.profile_picture = request.FILES['profile_picture']
            doctor.save()
            messages.success(request, 'Profile picture updated successfully!')
        else:
            # Handle other profile updates
            doctor.phone_number = request.POST.get('phone_number')
            doctor.address = request.POST.get('address')
            doctor.certifications = request.POST.get('certifications')
            doctor.save()
            messages.success(request, 'Profile updated successfully!')
        return redirect('doctor_profile')
    
    context = {'doctor': doctor}
    return render(request, 'doctor/doc_profile.html', context)

@user_passes_test(is_doctor)
def manage_availability(request):
    doctor = get_object_or_404(DoctorProfile, user=request.user)
    if request.method == 'POST':
        # Clear existing availability
        DoctorAvailability.objects.filter(doctor=doctor).delete()
        
        # Add new availability slots
        days = request.POST.getlist('day')
        start_times = request.POST.getlist('start_time')
        end_times = request.POST.getlist('end_time')
        
        for day, start, end in zip(days, start_times, end_times):
            DoctorAvailability.objects.create(
                doctor=doctor,
                day_of_week=day,
                start_time=start,
                end_time=end
            )
        messages.success(request, 'Availability updated successfully!')
        return redirect('manage_availability')
    
    availability = DoctorAvailability.objects.filter(doctor=doctor)
    context = {
        'doctor': doctor,
        'availability': availability
    }
    return render(request, 'shared/availability.html', context)

def is_admin_or_superadmin(user):
    return user.is_authenticated and user.userprofile.role.name in ['SUPER_ADMIN', 'ADMIN']

def privacy_policy(request):
    return render(request, 'privacy.html')

def terms_conditions(request):
    return render(request, 'terms.html')

@login_required
@permission_required('hmsapp.can_view_patients')
def view_patients(request):
    # Your view code here
    pass

class DoctorDashboardView(PermissionRequiredMixin, View):
    permission_required = 'hmsapp.can_access_doctor_dashboard'
    # Your view code here

@login_required
@admin_required
def manage_doctors(request):
    search_query = request.GET.get('search', '')
    specialty = request.GET.get('specialty')
    
    doctors = DoctorProfile.objects.all()
    
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(license_number__icontains=search_query)
        )
    
    if specialty:
        doctors = doctors.filter(specialty_id=specialty)
    
    context = {
        'doctors': doctors,
        'specialties': Specialty.objects.all()
    }
    return render(request, 'hosp_admin/manage_doctors.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def manage_patients(request):
    # Update ages for all patients
    patients = Patient.objects.all()
    for patient in patients:
        if patient.age != patient.calculated_age:
            patient.save()  # This will trigger the age recalculation

    # Your existing search logic
    search_query = request.GET.get('search', '')
    min_age = request.GET.get('min_age')
    max_age = request.GET.get('max_age')
    gender = request.GET.get('gender')

    if search_query:
        patients = patients.filter(
            Q(patient_name__icontains=search_query) |
            Q(patient_id__icontains=search_query)
        )
    
    if gender:
        patients = patients.filter(gender=gender)
    
    if min_age:
        patients = patients.filter(age__gte=min_age)
    
    if max_age:
        patients = patients.filter(age__lte=max_age)

    context = {
        'patients': patients,
        'request': request
    }
    
    return render(request, 'shared/manage_patients.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def manage_appointments(request):
    search_query = request.GET.get('search', '')
    date_filter = request.GET.get('date')
    status_filter = request.GET.get('status')
    
    appointments = Appointment.objects.all()
    
    if search_query:
        appointments = appointments.filter(
            Q(patient__user__first_name__icontains=search_query) |
            Q(patient__user__last_name__icontains=search_query) |
            Q(doctor__user__first_name__icontains=search_query) |
            Q(doctor__user__last_name__icontains=search_query)
        )
    
    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)
    
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    context = {
        'appointments': appointments.order_by('appointment_date', 'appointment_time'),
        'doctors': DoctorProfile.objects.all(),
        'patients': Patient.objects.all()
    }
    return render(request, 'shared/manage_appointments.html', context)

@login_required
@admin_required
def manage_staff(request):
    search_query = request.GET.get('search', '')
    
    # Base queryset
    staff_members = StaffProfile.objects.all()
    
    # Apply search filter if search_query exists
    if search_query:
        staff_members = staff_members.filter(
            Q(staff_id__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    context = {
        'staff_members': staff_members,
        'search_query': search_query,
    }
    return render(request, 'hosp_admin/manage_staff.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def manage_bills(request):
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status')
    
    bills = Bill.objects.select_related('patient', 'treatment')
    
    if search_query:
        bills = bills.filter(
            Q(patient__user__first_name__icontains=search_query) |
            Q(patient__user__last_name__icontains=search_query) |
            Q(bill_number__icontains=search_query)
        )
    
    if status_filter:
        bills = bills.filter(payment_status=status_filter)
    
    # Calculate totals as before
    total_paid = bills.aggregate(total_payments=Sum('paid_amount'))['total_payments'] or Decimal('0.00')
    total_pending = bills.filter(
        payment_status__in=['PENDING', 'PARTIALLY_PAID', 'OVERDUE']
    ).aggregate(
        pending_amount=Sum('amount') - Sum('paid_amount')
    )['pending_amount'] or Decimal('0.00')
    
    context = {
        'bills': bills.order_by('-created_at'),
        'total_paid': total_paid,
        'total_pending': total_pending,
    }
    return render(request, 'shared/manage_bills.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def view_bill(request, bill_id):
    """
    View function to display a detailed bill with print capability
    """
    bill = get_object_or_404(Bill, id=bill_id)
    
    context = {
        'bill': bill,
    }
    
    return render(request, 'shared/view_bill.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def create_bill(request):
    if request.method == 'POST':
        try:
            # Check if treatment already has a bill
            treatment_id = request.POST['treatment']
            if Bill.objects.filter(treatment_id=treatment_id).exists():
                messages.error(request, 'This treatment already has a bill!')
                return redirect('create_bill')

            # Create new bill
            bill = Bill.objects.create(
                patient_id=request.POST['patient'],
                treatment_id=treatment_id,
                amount=request.POST['amount'],
                due_date=request.POST['due_date']
            )
            messages.success(request, 'Bill created successfully!')
            return redirect('view_bill', bill_id=bill.id)
        except Exception as e:
            messages.error(request, f'Error creating bill: {str(e)}')
    
    # Get only treatments that don't have bills yet
    treatments = Treatment.objects.filter(bill__isnull=True).select_related('patient', 'doctor')
    
    context = {
        'treatments': treatments,
        'today': date.today()
    }
    return render(request, 'shared/create_bill.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def edit_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    payment_status_choices = Bill.PAYMENT_STATUS
    
    if request.method == 'POST':
        try:
            if bill.paid_amount == 0:
                bill.amount = request.POST.get('amount')
            bill.due_date = request.POST.get('due_date')
            bill.payment_status = request.POST.get('payment_status')
            bill.save()
            messages.success(request, 'Bill updated successfully!')
            return redirect('view_bill', bill_id=bill.id)
        except Exception as e:
            messages.error(request, f'Error updating bill: {str(e)}')
    
    context = {
        'bill': bill,
        'payment_status_choices': payment_status_choices
    }
    return render(request, 'shared/edit_bill.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def delete_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    bill.delete()
    messages.success(request, 'Bill deleted successfully!')
    return redirect('manage_bills')

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def record_payment(request, bill_id):
    if request.method == 'POST':
        bill = get_object_or_404(Bill, id=bill_id)
        try:
            payment_amount = Decimal(request.POST['amount'])
            if payment_amount <= (bill.amount - bill.paid_amount):
                # Create new payment record
                Payment.objects.create(
                    bill=bill,
                    amount=payment_amount,
                    payment_date=date.today(),
                    payment_method=request.POST['payment_method']
                )
                messages.success(request, 'Payment recorded successfully!')
            else:
                messages.error(request, 'Payment amount exceeds remaining balance!')
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
    
    return redirect('view_bill', bill_id=bill_id)

@login_required
def view_doctor(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    context = {
        'doctor': doctor
    }
    return render(request, 'shared/view_doctor.html', context)

@login_required
@admin_required
def edit_doctor(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    specialties = Specialty.objects.all()
    
    if request.method == 'POST':
        try:
            # Update User model fields
            doctor.user.first_name = request.POST.get('first_name')
            doctor.user.last_name = request.POST.get('last_name')
            doctor.user.email = request.POST.get('email')
            doctor.user.save()
            
            # Update DoctorProfile fields
            doctor.specialty_id = request.POST.get('specialty')
            doctor.license_number = request.POST.get('license_number')
            doctor.phone_number = request.POST.get('phone_number')
            doctor.address = request.POST.get('address')
            
            # Handle profile picture update
            if 'profile_picture' in request.FILES:
                doctor.profile_picture = request.FILES['profile_picture']
            
            doctor.save()
            messages.success(request, 'Doctor information updated successfully!')
            return redirect('view_doctor', doctor_id=doctor.id)
            
        except Exception as e:
            messages.error(request, f'Error updating doctor: {str(e)}')
    
    context = {
        'doctor': doctor,
        'specialties': specialties
    }
    return render(request, 'hosp_admin/edit_doctor.html', context)

@login_required
@admin_required
def delete_doctor(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    try:
        # Delete the user (this will cascade delete the doctor profile)
        doctor.user.delete()
        messages.success(request, 'Doctor deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting doctor: {str(e)}')
    
    return redirect('manage_doctors')

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def view_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-record_date')

    context = {
        'patient': patient,
        'medical_records': medical_records
    }
    return render(request, 'shared/view_patient.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def edit_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    if request.method == 'POST':
        try:
            # Convert string date to datetime.date object
            date_of_birth = datetime.strptime(
                request.POST.get('date_of_birth'), 
                '%Y-%m-%d'
            ).date()
            
            # Calculate age
            today = datetime.now().date()
            age = relativedelta(today, date_of_birth).years
            
            # Validate age (optional)
            if age < 0:
                messages.error(request, "Date of birth cannot be in the future")
                return redirect('edit_patient', patient_id=patient_id)
            
            # Update patient data
            patient.date_of_birth = date_of_birth
            patient.gender = request.POST.get('gender')
            patient.blood_group = request.POST.get('blood_group')
            patient.phone_number = request.POST.get('phone_number')
            patient.address = request.POST.get('address')
            patient.nationality = request.POST.get('nationality')
            patient.emergency_contact_name = request.POST.get('emergency_contact_name')
            patient.emergency_contact_phone = request.POST.get('emergency_contact_phone')
            patient.medical_history = request.POST.get('medical_history')
            
            # Handle profile picture update
            if 'profile_picture' in request.FILES:
                patient.profile_picture = request.FILES['profile_picture']
            
            patient.save()
            messages.success(request, 'Patient information updated successfully!')
            return redirect('view_patient', patient_id=patient.id)
            
        except ValueError as e:
            messages.error(request, f"Error updating patient: Invalid date format")
            return redirect('edit_patient', patient_id=patient_id)
        except Exception as e:
            messages.error(request, f"Error updating patient: {str(e)}")
            return redirect('edit_patient', patient_id=patient_id)

    context = {
        'patient': patient,
        'blood_groups': blood_groups
    }
    return render(request, 'shared/edit_patient.html', context)

@login_required
def delete_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    try:
        patient.user.delete()
        messages.success(request, 'Patient deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting patient: {str(e)}')
    
    return redirect('manage_patients')

@login_required
def view_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    context = {
        'appointment': appointment
    }
    return render(request, 'shared/view_appointment.html', context)

@login_required
def edit_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        try:
            # Update appointment fields
            appointment.patient_id = request.POST.get('patient')
            appointment.doctor_id = request.POST.get('doctor')
            appointment.appointment_date = request.POST.get('appointment_date')
            appointment.appointment_time = request.POST.get('appointment_time')
            appointment.notes = request.POST.get('notes', '')
            appointment.status = request.POST.get('status', appointment.status)
            
            appointment.save()
            messages.success(request, 'Appointment updated successfully!')
            return redirect('view_appointment', appointment_id=appointment.id)
            
        except Exception as e:
            messages.error(request, f'Error updating appointment: {str(e)}')

    context = {
        'appointment': appointment,
        'doctors': DoctorProfile.objects.all(),
        'patients': Patient.objects.all(),
        'today': date.today(),
        'statuses': ['SCHEDULED', 'COMPLETED', 'CANCELLED']
    }
    return render(request, 'shared/edit_appointment.html', context)

@login_required
def delete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    try:
        # Instead of deleting, we'll mark it as cancelled
        appointment.status = 'CANCELLED'
        appointment.save()
        messages.success(request, 'Appointment cancelled successfully!')
    except Exception as e:
        messages.error(request, f'Error cancelling appointment: {str(e)}')
    
    return redirect('manage_appointments')

@login_required
def view_staff(request, staff_id):
    staff = get_object_or_404(StaffProfile, id=staff_id)
    context = {
        'staff': staff
    }
    return render(request, 'hosp_admin/view_staff.html', context)

@login_required
def edit_staff(request, staff_id):
    staff = get_object_or_404(StaffProfile, id=staff_id)
    
    if request.method == 'POST':
        try:
            # Update User model fields
            staff.user.first_name = request.POST.get('first_name')
            staff.user.last_name = request.POST.get('last_name')
            staff.user.email = request.POST.get('email')
            staff.user.save()
            
            # Update StaffProfile fields
            staff.role = request.POST.get('role')
            staff.department = request.POST.get('department')
            staff.phone_number = request.POST.get('phone_number')
            staff.address = request.POST.get('address')
            
            # Handle profile picture update
            if 'profile_picture' in request.FILES:
                staff.profile_picture = request.FILES['profile_picture']
            
            staff.save()
            messages.success(request, 'Staff information updated successfully!')
            return redirect('view_staff', staff_id=staff.id)
            
        except Exception as e:
            messages.error(request, f'Error updating staff: {str(e)}')
    
    context = {
        'staff': staff,
        'roles': ['NURSE', 'RECEPTIONIST', 'LAB_TECHNICIAN', 'PHARMACIST', 'ADMIN_STAFF'],
        'departments': ['EMERGENCY', 'OUTPATIENT', 'INPATIENT', 'LABORATORY', 'PHARMACY', 'ADMINISTRATION']
    }
    return render(request, 'hosp_admin/edit_staff.html', context)

@login_required
def delete_staff(request, staff_id):
    staff = get_object_or_404(StaffProfile, id=staff_id)
    try:
        # Delete the user (this will cascade delete the staff profile)
        staff.user.delete()
        messages.success(request, 'Staff member deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting staff member: {str(e)}')
    
    return redirect('manage_staff')

@login_required
@staff_required
def staff_dashboard(request):
    context = {
        'staff': get_object_or_404(StaffProfile, user=request.user),
        'todays_appointments': Appointment.objects.filter(
            appointment_date=date.today()
        ).order_by('appointment_time'),
        'recent_patients': Patient.objects.order_by('-created_at')[:5],
        'pending_bills': Bill.objects.filter(
            payment_status__in=['UNPAID', 'PARTIALLY_PAID']
        ).count(),
        'total_doctors': DoctorProfile.objects.count()
    }
    return render(request, 'staff/staff_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def manage_treatments(request):
    search_query = request.GET.get('search', '')
    date_filter = request.GET.get('date')
    
    treatments = Treatment.objects.all()
    
    if search_query:
        treatments = treatments.filter(
            Q(patient__user__first_name__icontains=search_query) |
            Q(patient__user__last_name__icontains=search_query) |
            Q(doctor__user__first_name__icontains=search_query) |
            Q(doctor__user__last_name__icontains=search_query)
        )
    
    if date_filter:
        treatments = treatments.filter(created_at__date=date_filter)
    
    context = {
        'treatments': treatments.order_by('-created_at'),
        'doctors': DoctorProfile.objects.all(),
        'patients': Patient.objects.all()
    }
    return render(request, 'shared/manage_treatments.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def view_treatment(request, treatment_id):
    treatment = get_object_or_404(Treatment, id=treatment_id)

    context = {
        'treatment': treatment
    }
    return render(request, 'shared/view_treatment.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def edit_treatment(request, treatment_id):
    treatment = get_object_or_404(Treatment, id=treatment_id)
    
    if request.method == 'POST':
        try:
            treatment.patient_id = request.POST.get('patient')
            treatment.doctor_id = request.POST.get('doctor')
            treatment.chief_complaint = request.POST.get('chief_complaint')
            treatment.examination_findings = request.POST.get('examination_findings')
            treatment.diagnosis = request.POST.get('diagnosis')
            treatment.prescription = request.POST.get('prescription')
            treatment.notes = request.POST.get('notes', '')
            
            treatment.save()
            messages.success(request, 'Treatment updated successfully!')
            return redirect('view_treatment', treatment_id=treatment.id)
            
        except Exception as e:
            messages.error(request, f'Error updating treatment: {str(e)}')

    context = {
        'treatment': treatment,
        'doctors': DoctorProfile.objects.all(),
        'patients': Patient.objects.all()
    }
    return render(request, 'shared/edit_treatment.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def delete_treatment(request, treatment_id):
    treatment = get_object_or_404(Treatment, id=treatment_id)
    try:
        treatment.delete()
        messages.success(request, 'Treatment deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting treatment: {str(e)}')
    
    return redirect('manage_treatments')

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def add_treatment(request):
    if request.method == 'POST':
        try:
            patient_id = request.POST.get('patient')
            doctor_id = request.POST.get('doctor')
            chief_complaint = request.POST.get('chief_complaint')
            examination_findings = request.POST.get('examination_findings')
            diagnosis = request.POST.get('diagnosis')
            prescription = request.POST.get('prescription')
            notes = request.POST.get('notes', '')
            
            treatment = Treatment.objects.create(
                patient_id=patient_id,
                doctor_id=doctor_id,
                chief_complaint=chief_complaint,
                examination_findings=examination_findings,
                diagnosis=diagnosis,
                prescription=prescription,
                notes=notes
            )
            
            messages.success(request, 'Treatment added successfully!')
            return redirect('view_treatment', treatment_id=treatment.id)
            
        except Exception as e:
            messages.error(request, f'Error adding treatment: {str(e)}')

    context = {
        'doctors': DoctorProfile.objects.all(),
        'patients': Patient.objects.all()
    }
    return render(request, 'shared/add_treatment.html', context)

@login_required
@user_passes_test(is_doctor)
def google_calendar_auth(request):
    """Start Google Calendar OAuth flow"""
    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/calendar.events'],
        redirect_uri=request.build_absolute_uri(reverse('google_calendar_callback'))
    )
    
    # Force account selection for better account switching
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='select_account'  # Force account selection even if already logged in
    )
    
    request.session['google_auth_state'] = state
    return redirect(authorization_url)

@login_required
@user_passes_test(is_doctor)
def google_calendar_callback(request):
    """Handle Google Calendar OAuth callback"""
    state = request.session['google_auth_state']
    
    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/calendar.events'],
        state=state,
        redirect_uri=request.build_absolute_uri(reverse('google_calendar_callback'))
    )
    
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials
    
    doctor = request.user.doctorprofile
    doctor.google_calendar_credentials = credentials.to_json()
    doctor.google_calendar_enabled = True
    doctor.save()
    
    messages.success(request, 'Successfully connected to Google Calendar!')
    return redirect('doctor_profile')

@login_required
@user_passes_test(is_doctor)
def google_calendar_disconnect(request):
    """Disconnect Google Calendar integration"""
    doctor = request.user.doctorprofile
    doctor.google_calendar_credentials = None
    doctor.google_calendar_enabled = False
    doctor.save()
    
    messages.success(request, 'Google Calendar disconnected successfully.')
    return redirect('doctor_profile')

@login_required
def find_next_slot(request):
    """API endpoint to find the next available slot for a doctor"""
    doctor_id = request.GET.get('doctor')
    if not doctor_id:
        return JsonResponse({'success': False, 'message': 'Doctor ID is required'})

    try:
        doctor = DoctorProfile.objects.get(id=doctor_id)
        current_datetime = timezone.now()
        
        # Look for slots in the next 7 days
        for days_ahead in range(7):
            check_date = current_datetime.date() + timedelta(days=days_ahead)
            current_weekday = check_date.weekday()
            
            # Get availability slots for the day
            availability_slots = get_doctor_availability(doctor, current_weekday)
            
            if not availability_slots:
                continue
                
            # Get all appointments for the doctor on this day
            day_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=check_date,
                status='SCHEDULED'
            ).order_by('appointment_time')

            # Default slot duration in minutes
            slot_duration = 30

            # Check each availability slot
            for start_time, end_time in availability_slots:
                current_time = start_time
                if check_date == timezone.now().date():
                    # If it's today, start from current time (rounded up to next slot)
                    current_time = max(
                        current_time,
                        (timezone.now() + timedelta(minutes=(slot_duration - timezone.now().minute % slot_duration))).time()
                    )

                # Find the first available slot
                while current_time < end_time:
                    slot_datetime = datetime.combine(check_date, current_time)
                    
                    # Check if this slot conflicts with any existing appointment
                    slot_is_available = not day_appointments.filter(
                        appointment_time__gte=current_time,
                        appointment_time__lt=(datetime.combine(date.min, current_time) + timedelta(minutes=slot_duration)).time()
                    ).exists()

                    if slot_is_available:
                        return JsonResponse({
                            'success': True,
                            'date': check_date.isoformat(),
                            'time': current_time.strftime('%H:%M'),
                            'message': 'Available slot found'
                        })

                    # Move to next slot
                    slot_datetime += timedelta(minutes=slot_duration)
                    current_time = slot_datetime.time()

        # If we get here, no slots were available in the next 7 days
        return JsonResponse({
            'success': False,
            'message': 'No available slots found in the next 7 days'
        })

    except DoctorProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Doctor not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@admin_required
def view_user_activities(request):
    """View for administrators to see user activities"""
    
    # Get filter parameters
    user_filter = request.GET.get('user')
    activity_type = request.GET.get('activity_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    activities = UserActivity.objects.all()
    
    # Apply filters
    if user_filter:
        activities = activities.filter(user__username__icontains=user_filter)
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    if date_from:
        activities = activities.filter(timestamp__gte=date_from)
    if date_to:
        activities = activities.filter(timestamp__lte=date_to)
    
    # Pagination
    paginator = Paginator(activities, 50)  # Show 50 activities per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'activity_types': UserActivity.ACTIVITY_TYPES,
        'users': User.objects.all(),
    }
    
    return render(request, 'hosp_admin/user_activities.html', context)

@login_required
@admin_required
def view_login_activities(request):
    """View for administrators to see login activities"""
    
    # Get filter parameters
    user_filter = request.GET.get('user')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    login_activities = LoginActivity.objects.all()
    
    # Apply filters
    if user_filter:
        login_activities = login_activities.filter(user__username__icontains=user_filter)
    if date_from:
        login_activities = login_activities.filter(login_datetime__gte=date_from)
    if date_to:
        login_activities = login_activities.filter(login_datetime__lte=date_to)
    
    # Pagination
    paginator = Paginator(login_activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': User.objects.all(),
    }
    
    return render(request, 'hosp_admin/login_activities.html', context)

@track_activity('CREATE', 'Created new appointment')
def create_appointment(request):
    # Your view code here
    pass

@track_activity('UPDATE', 'Updated patient information')
def update_patient(request):
    # Your view code here
    pass

@login_required
@admin_required
def analytics_dashboard(request):
    """Main analytics dashboard view"""
    
    # Get date range from request or default to last 12 months
    end_date = timezone.now().date()
    start_date = request.GET.get('start_date', (end_date - timedelta(days=365)).isoformat())
    end_date = request.GET.get('end_date', end_date.isoformat())
    
    # Convert to datetime objects
    start_date = datetime.fromisoformat(start_date)
    end_date = datetime.fromisoformat(end_date)
    
    # Get key metrics
    metrics = {
        'total_patients': Patient.objects.count(),
        'total_appointments': Appointment.objects.filter(
            appointment_date__range=[start_date, end_date]
        ).count(),
        'total_revenue': Bill.objects.filter(
            created_at__range=[start_date, end_date]
        ).aggregate(total=Sum('paid_amount'))['total'] or 0,
        'avg_daily_appointments': Appointment.objects.filter(
            appointment_date__range=[start_date, end_date]
        ).count() / max((end_date - start_date).days, 1)
    }
    
    # Get appointment trends by month
    appointment_trends = list(
        Appointment.objects.filter(appointment_date__range=[start_date, end_date])
        .annotate(month=TruncMonth('appointment_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    
    # Format appointment trends for pie chart
    formatted_appointment_trends = [
        {
            'month': item['month'].strftime('%B %Y'),
            'count': item['count']
        } for item in appointment_trends
    ]
    
    # Get revenue trends by month
    revenue_trends = list(
        Bill.objects.filter(created_at__range=[start_date, end_date])
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('paid_amount'))
        .order_by('month')
    )
    
    # Format revenue trends for pie chart
    formatted_revenue_trends = [
        {
            'month': item['month'].strftime('%B %Y'),
            'total': float(item['total'] or 0)
        } for item in revenue_trends
    ]
    
    # Get patient demographics with proper formatting
    gender_distribution = dict(
        Patient.objects.values('gender')
        .annotate(count=Count('id'))
        .values_list('gender', 'count')
    )
    
    # Format demographics data
    demographics = {
        'gender_distribution': gender_distribution,
        'age_distribution': get_age_distribution()
    }
    
    # Get top performing doctors
    top_doctors = (
        Appointment.objects.filter(appointment_date__range=[start_date, end_date])
        .values('doctor__user__first_name', 'doctor__user__last_name')
        .annotate(appointment_count=Count('id'))
        .order_by('-appointment_count')[:5]
    )

    # Add debug data
    print("Debug Data:")
    print("Appointment Trends:", formatted_appointment_trends)
    print("Revenue Trends:", formatted_revenue_trends)
    print("Demographics:", demographics)
    
    # Ensure data is not empty
    if not formatted_appointment_trends:
        formatted_appointment_trends = [{'month': 'No Data', 'count': 0}]
    if not formatted_revenue_trends:
        formatted_revenue_trends = [{'month': 'No Data', 'total': 0}]
    if not demographics['gender_distribution']:
        demographics['gender_distribution'] = {'No Data': 0}
    if not demographics['age_distribution']:
        demographics['age_distribution'] = {'No Data': 0}
    
    context = {
        'metrics': metrics,
        'appointment_trends': formatted_appointment_trends,
        'revenue_trends': formatted_revenue_trends,
        'demographics': demographics,
        'top_doctors': top_doctors,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
    }
    
    return render(request, 'hosp_admin/analytics_dashboard.html', context)

@login_required
@admin_required
def generate_report(request):
    """Generate customized reports based on configuration"""
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        filters = json.loads(request.POST.get('filters', '{}'))
        
        # Generate report based on type
        if report_type == 'PATIENT_DEMOGRAPHICS':
            data = generate_demographics_report(start_date, end_date, filters)
        elif report_type == 'REVENUE_ANALYSIS':
            data = generate_revenue_report(start_date, end_date, filters)
        elif report_type == 'APPOINTMENT_TRENDS':
            data = generate_appointment_report(start_date, end_date, filters)
        elif report_type == 'SERVICE_UTILIZATION':
            data = generate_service_report(start_date, end_date, filters)
        else:
            data = {}
        
        # Save report configuration if requested
        if request.POST.get('save_config'):
            ReportConfiguration.objects.create(
                name=request.POST.get('report_name'),
                report_type=report_type,
                frequency=request.POST.get('frequency'),
                filters=filters,
                created_by=request.user
            )
        
        return render(request, 'hosp_admin/report_result.html', {'data': data})
    
    # For GET requests, show the report configuration form
    context = {
        'report_types': ReportConfiguration.REPORT_TYPES,
        'frequencies': ReportConfiguration.FREQUENCY_CHOICES,
        'saved_configs': ReportConfiguration.objects.filter(created_by=request.user)
    }
    return render(request, 'hosp_admin/generate_report.html', context)

def get_age_distribution():
    """Helper function to calculate patient age distribution"""
    age_ranges = [(0, 18), (19, 30), (31, 45), (46, 60), (61, float('inf'))]
    distribution = defaultdict(int)
    
    for patient in Patient.objects.all():
        age = (timezone.now().date() - patient.date_of_birth).days // 365
        for start, end in age_ranges:
            if start <= age <= end:
                range_label = f"{start}-{end if end != float('inf') else '+'}"
                distribution[range_label] += 1
                break
    
    return dict(distribution)

def generate_demographics_report(start_date, end_date, filters):
    """Generate detailed patient demographics report"""
    patients = Patient.objects.filter(created_at__range=[start_date, end_date])
    
    # Apply filters
    if filters.get('gender'):
        patients = patients.filter(gender=filters['gender'])
    if filters.get('age_min'):
        patients = patients.filter(date_of_birth__lte=timezone.now().date() - timedelta(days=int(filters['age_min'])*365))
    if filters.get('age_max'):
        patients = patients.filter(date_of_birth__gte=timezone.now().date() - timedelta(days=int(filters['age_max'])*365))
    
    return {
        'total_patients': patients.count(),
        'gender_distribution': dict(patients.values('gender').annotate(count=Count('id')).values_list('gender', 'count')),
        'age_distribution': get_age_distribution(),
        'nationality_distribution': dict(patients.values('nationality').annotate(count=Count('id')).values_list('nationality', 'count')),
        'monthly_registrations': list(
            patients.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
    }

def generate_revenue_report(start_date, end_date, filters):
    """Generate detailed revenue analysis report"""
    bills = Bill.objects.filter(created_at__range=[start_date, end_date])
    
    # Apply filters
    if filters.get('payment_status'):
        bills = bills.filter(payment_status=filters['payment_status'])
    
    return {
        'total_revenue': bills.aggregate(total=Sum('paid_amount'))['total'] or 0,
        'average_bill_amount': bills.aggregate(avg=Avg('amount'))['avg'] or 0,
        'payment_status_distribution': dict(
            bills.values('payment_status')
            .annotate(count=Count('id'), total=Sum('amount'))
            .values_list('payment_status', 'total')
        ),
        'monthly_revenue': list(
            bills.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum('paid_amount'))
            .order_by('month')
        ),
        'outstanding_amount': bills.filter(
            payment_status__in=['PENDING', 'PARTIALLY_PAID']
        ).aggregate(total=Sum(F('amount') - F('paid_amount')))['total'] or 0
    }

def generate_appointment_report(start_date, end_date, filters):
    """Generate detailed appointment trends report"""
    appointments = Appointment.objects.filter(appointment_date__range=[start_date, end_date])
    
    # Apply filters
    if filters.get('doctor'):
        appointments = appointments.filter(doctor_id=filters['doctor'])
    if filters.get('status'):
        appointments = appointments.filter(status=filters['status'])
    
    return {
        'total_appointments': appointments.count(),
        'status_distribution': dict(
            appointments.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        ),
        'doctor_distribution': dict(
            appointments.values('doctor__user__first_name', 'doctor__user__last_name')
            .annotate(count=Count('id'))
            .values_list('doctor__user__first_name', 'count')
        ),
        'monthly_trends': list(
            appointments.annotate(month=TruncMonth('appointment_date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
    }

def generate_service_report(start_date, end_date, filters):
    """Generate service utilization report"""
    treatments = Treatment.objects.filter(created_at__range=[start_date, end_date])
    
    if filters.get('doctor'):
        treatments = treatments.filter(doctor_id=filters['doctor'])
        
    return {
        'total_treatments': treatments.count(),
        'treatments_by_doctor': dict(
            treatments.values('doctor__user__first_name')
            .annotate(count=Count('id'))
            .values_list('doctor__user__first_name', 'count')
        ),
        'monthly_treatments': list(
            treatments.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
    }

@login_required
def all_doctors(request):
    doctors = DoctorProfile.objects.all().select_related('user')
    context = {
        'doctors': doctors,
        'title': 'All Doctors'
    }
    return render(request, 'staff/all_doctors.html', context)

def generate_upi_qr(amount, upi_id, name, transaction_note):
    """Generate UPI QR code"""
    upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={transaction_note}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert image to base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_code = base64.b64encode(buffer.getvalue()).decode()
    return qr_code

@login_required
def upi_payment(request, bill_id):
    """Handle UPI payment for a bill"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Get payment amount from POST or default to remaining amount
    payment_amount = request.POST.get('payment_amount', bill.remaining_amount)
    
    # Your hospital's UPI ID
    upi_id = settings.HOSPITAL_UPI_ID
    transaction_note = f"Bill#{bill.id} for {bill.patient.patient_name}"
    
    # Generate QR code with the specified amount
    qr_code = generate_upi_qr(
        amount=payment_amount,
        upi_id=upi_id,
        name="Hospital Name",
        transaction_note=transaction_note
    )
    
    context = {
        'bill': bill,
        'qr_code': qr_code,
        'upi_id': upi_id,
        'payment_amount': payment_amount
    }
    return render(request, 'shared/payment.html', context)

@login_required
def verify_upi_payment(request, bill_id):
    """Verify UPI payment and update bill status"""
    if request.method == 'POST':
        bill = get_object_or_404(Bill, id=bill_id)
        utr = request.POST.get('utr')
        payment_amount = Decimal(request.POST.get('payment_amount', 0))
        
        # Validate payment amount
        if payment_amount <= 0 or payment_amount > bill.remaining_amount:
            messages.error(request, 'Invalid payment amount')
            return redirect('upi_payment', bill_id=bill.id)
        
        # Create payment record with UTR
        Payment.objects.create(
            bill=bill,
            amount=payment_amount,
            payment_date=timezone.now().date(),
            payment_method='UPI',
            transaction_id=utr,  # Store the UTR
            notes=f"UPI Payment with UTR: {utr}"
        )
        
        messages.success(request, 'Payment recorded successfully!')
        return redirect('view_bill', bill_id=bill.id)
    
    return redirect('upi_payment', bill_id=bill_id)

@login_required
@permission_required('hmsapp.add_patient')
def add_patient(request):
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            date_of_birth = request.POST.get('date_of_birth')
            gender = request.POST.get('gender')
            blood_group = request.POST.get('blood_group')
            nationality = request.POST.get('nationality')
            address = request.POST.get('address')
            emergency_contact_name = request.POST.get('emergency_contact_name')
            emergency_contact_phone = request.POST.get('emergency_contact_phone')

            # Create user account
            username = f"patient_{phone_number}"
            user = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email if email else ''
            )

            # Create patient profile
            patient = Patient.objects.create(
                user=user,
                patient_name=f"{first_name} {last_name}",
                phone_number=phone_number,
                date_of_birth=date_of_birth,
                gender=gender,
                blood_group=blood_group,
                nationality=nationality or 'Not Specified',
                address=address,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone
            )

            messages.success(request, 'Patient added successfully!')
            return JsonResponse({
                'status': 'success',
                'message': 'Patient added successfully!',
                'redirect_url': reverse('view_patient', args=[patient.id])
            })

        except Exception as e:
            messages.error(request, f'Error adding patient: {str(e)}')
            return JsonResponse({
                'status': 'error',
                'message': f'Error adding patient: {str(e)}'
            }, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def complete_appointment(request, appointment_id):
    try:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        # Update appointment status
        appointment.status = 'COMPLETED'
        appointment.save()
        
        # Only try Google Calendar if doctor has valid credentials
        if (hasattr(appointment.doctor, 'google_calendar_enabled') and 
            appointment.doctor.google_calendar_enabled and 
            appointment.doctor.google_calendar_credentials):
            try:
                # Google Calendar logic would go here if needed
                pass
            except Exception as e:
                # Log the error but don't stop the appointment completion
                print(f"Google Calendar update failed: {str(e)}")
        
        messages.success(request, 'Appointment marked as completed successfully.')
        
    except Exception as e:
        messages.error(request, f'Error completing appointment: {str(e)}')
    
    return redirect('view_appointment', appointment_id=appointment_id)
