from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import time
from hmsapp.models import Doctor, Role, Specialty, DoctorAvailability

class Command(BaseCommand):
    help = 'Create a test doctor with proper role and availability'

    def handle(self, *args, **kwargs):
        try:
            # Ensure DOCTOR role exists
            doctor_role, _ = Role.objects.get_or_create(name='DOCTOR')

            # Create test specialty if it doesn't exist
            specialty, _ = Specialty.objects.get_or_create(
                specialty_name='General Medicine',
                description='General Medicine Department'
            )

            # Create test user if it doesn't exist
            username = 'testdoctor'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    password='testdoctor123',
                    email='testdoctor@example.com',
                    first_name='Test',
                    last_name='Doctor'
                )

                # Create doctor profile
                doctor = Doctor.objects.create(
                    user=user,
                    doc_name='Dr. Test Doctor',
                    specialty=specialty,
                    license_number='TEST123',
                    phone_number='1234567890',
                    address='123 Test Street'
                )

                # Create availability for weekdays
                weekday_schedule = [
                    {'day': 0, 'start': '09:00', 'end': '17:00'},  # Monday
                    {'day': 1, 'start': '09:00', 'end': '17:00'},  # Tuesday
                    {'day': 2, 'start': '09:00', 'end': '17:00'},  # Wednesday
                    {'day': 3, 'start': '09:00', 'end': '17:00'},  # Thursday
                    {'day': 4, 'start': '09:00', 'end': '17:00'},  # Friday
                ]

                for schedule in weekday_schedule:
                    DoctorAvailability.objects.create(
                        doctor=doctor,
                        day_of_week=schedule['day'],
                        start_time=time.fromisoformat(schedule['start']),
                        end_time=time.fromisoformat(schedule['end']),
                        is_available=True
                    )

                self.stdout.write(self.style.SUCCESS(
                    f'Successfully created test doctor with ID: {doctor.doctor_id}\n'
                    f'Username: {username}\n'
                    f'Password: testdoctor123\n'
                    f'Availability: Monday-Friday, 9 AM - 5 PM'
                ))
            else:
                self.stdout.write(self.style.WARNING('Test doctor already exists'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating test doctor: {str(e)}')) 