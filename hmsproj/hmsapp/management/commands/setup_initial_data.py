from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.management import call_command
from hmsapp.models import Role, UserProfile, Specialty

class Command(BaseCommand):
    help = 'Sets up initial data for the HMS system'

    def handle(self, *args, **kwargs):
        # First set up roles with proper permissions
        self.stdout.write('Setting up roles and permissions...')
        call_command('setup_roles')
        
        self.stdout.write('Creating super admin user...')
        # Create superuser
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        # Get the SUPER_ADMIN role
        super_admin_role = Role.objects.get(name='SUPER_ADMIN')
        
        # Update the existing UserProfile instead of creating a new one
        UserProfile.objects.filter(user=superuser).update(role=super_admin_role)

        self.stdout.write('Creating basic specialties...')
        # Create some basic specialties
        specialties = [
            'General Medicine',
            'Pediatrics',
            'Cardiology',
            'Orthopedics',
            'Dermatology',
            'Neurology',
            'Gynecology',
        ]
        for specialty in specialties:
            Specialty.objects.create(
                specialty_name=specialty,
                description=f'Department of {specialty}'
            )

        self.stdout.write(self.style.SUCCESS('Initial setup completed successfully!'))
        self.stdout.write(self.style.SUCCESS('Superuser created with:'))
        self.stdout.write('Username: admin')
        self.stdout.write('Password: admin123') 