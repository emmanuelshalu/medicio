from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from .models import *
from .decorators import admin_required, doctor_required, staff_required
from decimal import Decimal
from django.core.files.storage import FileSystemStorage
from google_auth_oauthlib.flow import Flow
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from django.db.models import Sum

def home(request):
    doctors = DoctorProfile.objects.all()
    specialties = Specialty.objects.all()
    context = {
        'doctors': doctors,
        'specialties': specialties,
    }
    return render(request, 'home.html', context)

def book_appointment(request):
    if request.method == 'POST':
        try:
            # Get form data
            patient_name = request.POST.get('patient_name')
            phone_number = request.POST.get('phone_number')
            doctor_id = request.POST.get('doctor')
            appointment_date = request.POST.get('appointment_date')
            appointment_time = request.POST.get('appointment_time')
            reason = request.POST.get('reason')
            notes = request.POST.get('notes', '')
            status = request.POST.get('status', 'SCHEDULED')

            # Create user for patient
            username = f"patient_{phone_number}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': patient_name.split()[0],
                    'last_name': ' '.join(patient_name.split()[1:]) if len(patient_name.split()) > 1 else ''
                }
            )

            # Get or create patient with all required fields
            patient, created = Patient.objects.get_or_create(
                phone_number=phone_number,
                defaults={
                    'user': user,
                    'patient_name': patient_name,
                    'date_of_birth': datetime.now().date(),  # Default value
                    'blood_group': 'O+',  # Default value
                    'gender': 'OTHER',  # Default value
                    'nationality': 'Not Specified',  # Default value
                    'emergency_contact_name': patient_name,  # Using patient name as default
                    'emergency_contact_phone': phone_number  # Using same phone number as default
                }
            )

            # Create appointment
            appointment = Appointment.objects.create(
                patient=patient,
                doctor_id=doctor_id,
                phone_number=phone_number,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                reason=reason,
                notes=notes,
                status=status
            )

            # Handle medical records file upload
            if 'medical_records' in request.FILES:
                medical_file = request.FILES['medical_records']
                
                # First create MedicalRecord entry
                medical_record = MedicalRecord.objects.create(
                    patient=patient,
                    record_date=datetime.now().date(),
                    description=f"Medical records uploaded during appointment booking - {reason}",
                    document=medical_file
                )
                
                # Then update appointment with the same file
                appointment.medical_records = medical_file
                appointment.save()

            messages.success(request, 'Appointment booked successfully!')
            return redirect('home')

        except Exception as e:
            print(f"Error details: {str(e)}")  # Add this for debugging
            messages.error(request, f'Error booking appointment: {str(e)}')
            return redirect('home')

    # If GET request, render the form
    doctors = DoctorProfile.objects.all()
    context = {
        'doctors': doctors,
    }
    return render(request, 'home.html', context)

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

@user_passes_test(is_doctor)
def view_patient(request, patient_id):
    doctor = get_object_or_404(DoctorProfile, user=request.user)
    patient = get_object_or_404(Patient, patient_id=patient_id)
    
    if request.method == 'POST' and 'upload_record' in request.POST:
        MedicalRecord.objects.create(
            patient=patient,
            record_date=request.POST.get('record_date'),
            description=request.POST.get('record_description'),
            document=request.FILES['record_document']
        )
        messages.success(request, 'Medical record uploaded successfully!')
        return redirect('view_patient', patient_id=patient_id)
    
    treatments = Treatment.objects.filter(doctor=doctor, patient=patient)
    appointments = Appointment.objects.filter(doctor=doctor, patient=patient)
    
    context = {
        'patient': patient,
        'treatments': treatments,
        'appointments': appointments
    }
    return render(request, 'shared/patient_detail.html', context)

@user_passes_test(is_doctor)
def add_treatment(request, appointment_id):
    doctor = get_object_or_404(DoctorProfile, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
    
    if request.method == 'POST':
        Treatment.objects.create(
            patient=appointment.patient,
            doctor=doctor,
            appointment=appointment,
            chief_complaint=request.POST.get('chief_complaint'),
            examination_findings=request.POST.get('examination_findings'),
            diagnosis=request.POST.get('diagnosis'),
            prescription=request.POST.get('prescription'),
            notes=request.POST.get('notes')
        )
        appointment.status = 'COMPLETED'
        appointment.save()
        messages.success(request, 'Treatment record added successfully!')
        return redirect('doctor_dashboard')
    
    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'

    context = {
        'base_template': base_template,
        'appointment': appointment,
        'patient': appointment.patient
    }
    return render(request, 'shared/add_treatment.html', context)

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
    if request.method == 'POST':
        try:
            # Create User account
            user = User.objects.create_user(
                username=request.POST['email'],
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name']
            )
            
            # Create DoctorProfile
            doctor = DoctorProfile(
                user=user,
                specialty_id=request.POST['specialty'],
                license_number=request.POST['license_number'],
                phone_number=request.POST['phone_number'],
                address=request.POST['address']
            )
            
            # Handle profile picture if uploaded
            if 'profile_picture' in request.FILES:
                doctor.profile_picture = request.FILES['profile_picture']
            
            doctor.save()
            
            messages.success(request, 'Doctor added successfully!')
            return redirect('manage_doctors')
            
        except Exception as e:
            # If there's an error, delete the user if it was created
            if 'user' in locals():
                user.delete()
            messages.error(request, f'Error adding doctor: {str(e)}')
            return redirect('manage_doctors')
    
    # For GET requests
    doctors = DoctorProfile.objects.all()
    specialties = Specialty.objects.all()
    
    context = {
        'doctors': doctors,
        'specialties': specialties
    }
    
    return render(request, 'hosp_admin/manage_doctors.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def manage_patients(request):
    if request.method == 'POST':
        print("POST request received")
        print("Form data:", request.POST)
        try:
            # Create User account
            user = User.objects.create_user(
                username=request.POST['email'],
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name']
            )
            print("User created:", user)
            
            # Calculate date of birth from age
            age = int(request.POST['age'])
            date_of_birth = datetime.now() - timedelta(days=age*365)
            
            # Create Patient profile with only the fields that exist in your model
            patient = Patient(
                user=user,
                patient_name=f"{user.first_name} {user.last_name}",
                date_of_birth=date_of_birth,
                blood_group=request.POST['blood_group'],
                gender=request.POST['gender'].upper(),
                nationality='Not Specified',
                phone_number=request.POST['phone_number'],
                address=request.POST['address'],
                emergency_contact_name='Not Specified',
                emergency_contact_phone='Not Specified',
                medical_history=''
            )
            
            if 'profile_picture' in request.FILES:
                patient.profile_picture = request.FILES['profile_picture']
            
            patient.save()
            print("Patient created:", patient)
            messages.success(request, 'Patient added successfully!')
            return redirect('manage_patients')
            
        except Exception as e:
            print("Error:", str(e))
            if 'user' in locals():
                user.delete()
            messages.error(request, f'Error adding patient: {str(e)}')
            return redirect('manage_patients')
        
    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'
    # For GET requests
    patients = Patient.objects.all()
    context = {
        'base_template': base_template,
        'patients': patients
    }
    
    return render(request, 'shared/manage_patients.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators', 'Doctors']).exists())
def manage_appointments(request):
    if request.method == 'POST':
        try:
            appointment = Appointment(
                patient_id=request.POST['patient'],
                doctor_id=request.POST['doctor'],
                appointment_date=request.POST['appointment_date'],
                appointment_time=request.POST['appointment_time'],
                notes=request.POST.get('notes', ''),
                status='SCHEDULED'
            )
            appointment.save()
            messages.success(request, 'Appointment scheduled successfully!')
            return redirect('manage_appointments')
            
        except Exception as e:
            messages.error(request, f'Error scheduling appointment: {str(e)}')
            return redirect('manage_appointments')
    
    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'
    
    context = {
        'base_template': base_template,
        'appointments': Appointment.objects.all().order_by('-appointment_date', '-appointment_time'),
        'doctors': DoctorProfile.objects.all(),
        'patients': Patient.objects.all(),
        'today': date.today(),
    }
    
    return render(request, 'shared/manage_appointments.html', context)

@login_required
@admin_required
def manage_staff(request):
    if request.method == 'POST':
        try:
            # Create User account
            user = User.objects.create_user(
                username=request.POST['email'],
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name']
            )
            
            # Create StaffProfile with correct field names from your model
            staff = StaffProfile(
                user=user,
                department=request.POST['department'],
                designation=request.POST['role'],  # Using 'role' input for designation
                phone_number=request.POST['phone_number'],
                address=request.POST.get('address', '')
            )
            
            if 'profile_picture' in request.FILES:
                staff.profile_picture = request.FILES['profile_picture']
            
            staff.save()
            messages.success(request, 'Staff member added successfully!')
            return redirect('manage_staff')
            
        except Exception as e:
            if 'user' in locals():
                user.delete()
            messages.error(request, f'Error adding staff member: {str(e)}')
            return redirect('manage_staff')
    
    staff_members = StaffProfile.objects.all()
    context = {
        'staff_members': staff_members
    }
    
    return render(request, 'hosp_admin/manage_staff.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def manage_bills(request):
    bills = Bill.objects.select_related('patient', 'treatment').all()
    
    # Calculate total payments
    total_paid = Bill.objects.aggregate(
        total_payments=Sum('paid_amount')
    )['total_payments'] or Decimal('0.00')

    # Calculate total pending amount (total amount - paid amount)
    total_pending = Bill.objects.filter(
        payment_status__in=['PENDING', 'PARTIALLY_PAID', 'OVERDUE']
    ).aggregate(
        pending_amount=Sum('amount') - Sum('paid_amount')
    )['pending_amount'] or Decimal('0.00')
    
    # Calculate other statistics
    total_bills = bills.count()
    pending_bills = bills.filter(payment_status='PENDING').count()
    overdue_bills = bills.filter(payment_status='OVERDUE').count()

    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'

    context = {
        'base_template': base_template,
        'bills': bills,
        'total_bills': total_bills,
        'pending_bills': pending_bills,
        'overdue_bills': overdue_bills,
        'total_paid': total_paid,
        'total_pending': total_pending,
    }
    return render(request, 'shared/manage_bills.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def view_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'
    context = {
        'base_template': base_template,
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

    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'
    
    context = {
        'base_template': base_template,
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
    
    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'

    context = {
        'base_template': base_template,
        'bill': bill,
        'payment_status_choices': payment_status_choices
    }
    return render(request, 'shared/edit_bill.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Staff', 'Administrators']).exists())
def record_payment(request, bill_id):
    if request.method == 'POST':
        bill = get_object_or_404(Bill, id=bill_id)
        try:
            payment_amount = Decimal(request.POST['amount'])
            if payment_amount <= (bill.amount - bill.paid_amount):
                bill.paid_amount += payment_amount
                bill.payment_date = date.today()
                bill.payment_method = request.POST['payment_method']
                
                if bill.paid_amount == bill.amount:
                    bill.payment_status = 'PAID'
                elif bill.paid_amount > 0:
                    bill.payment_status = 'PARTIALLY_PAID'
                
                bill.save()
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

    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'

    context = {
        'base_template': base_template,
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
            # Update User model fields
            patient.user.first_name = request.POST.get('first_name')
            patient.user.last_name = request.POST.get('last_name')
            patient.user.email = request.POST.get('email')
            patient.user.save()
            
            # Update Patient fields
            patient.patient_name = f"{patient.user.first_name} {patient.user.last_name}"
            patient.date_of_birth = request.POST.get('date_of_birth')
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
            
        except Exception as e:
            messages.error(request, f'Error updating patient: {str(e)}')

    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'
    
    context = {
        'base_template': base_template,
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

    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'
    context = {
        'base_template': base_template,
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
    # Check if user is authenticated and has the appropriate role
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'

    context = {
        'base_template': base_template,
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
    staff = get_object_or_404(StaffProfile, user=request.user)
    context = {
        'staff': staff,
        'todays_appointments': Appointment.objects.filter(
            appointment_date=date.today()
        ).order_by('appointment_time'),
        'recent_patients': Patient.objects.order_by('-created_at')[:5]
    }
    return render(request, 'staff/staff_dashboard.html', context)

@login_required
@staff_required
def manage_treatments(request):
    treatments = Treatment.objects.all().order_by('-created_at')
    context = {
        'treatments': treatments,
        'doctors': DoctorProfile.objects.all(),
        'patients': Patient.objects.all()
    }
    return render(request, 'staff/manage_treatments.html', context)

@login_required
@staff_required
def view_treatment(request, treatment_id):
    treatment = get_object_or_404(Treatment, id=treatment_id)
    context = {
        'treatment': treatment
    }
    return render(request, 'staff/view_treatment.html', context)

@login_required
@staff_required
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
    return render(request, 'staff/edit_treatment.html', context)

@login_required
@staff_required
def delete_treatment(request, treatment_id):
    treatment = get_object_or_404(Treatment, id=treatment_id)
    try:
        treatment.delete()
        messages.success(request, 'Treatment deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting treatment: {str(e)}')
    
    return redirect('manage_treatments')

@login_required
@staff_required
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
    return render(request, 'staff/add_treatment.html', context)

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