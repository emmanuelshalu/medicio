from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from hmsapp.models import Role, Doctor, Patient, Appointment, Treatment, Bill, Staff, MedicalRecord

class Command(BaseCommand):
    help = 'Sets up roles with appropriate permissions'

    def handle(self, *args, **kwargs):
        # Define models and their permissions for each role
        role_permissions = {
            'SUPER_ADMIN': {
                'models': ['user', 'role', 'userprofile', 'doctor', 'patient', 'specialty', 
                          'doctoravailability', 'appointment', 'treatment', 'bill', 'staff', 
                          'medicalrecord'],
                'permissions': ['add', 'change', 'delete', 'view']
            },
            'ADMIN': {
                'models': ['doctor', 'patient', 'specialty', 'doctoravailability', 
                          'appointment', 'treatment', 'bill', 'staff', 'medicalrecord'],
                'permissions': ['add', 'change', 'delete', 'view']
            },
            'DOCTOR': {
                'models': {
                    'patient': ['view'],
                    'appointment': ['view', 'change'],
                    'treatment': ['add', 'change', 'view'],
                    'doctoravailability': ['view', 'change'],
                    'medicalrecord': ['add', 'view']
                }
            },
            'STAFF': {
                'models': {
                    'patient': ['add', 'change', 'view'],
                    'appointment': ['add', 'change', 'view'],
                    'bill': ['add', 'change', 'view'],
                    'medicalrecord': ['add', 'view']
                }
            }
        }

        # Create roles and assign permissions
        for role_name, role_config in role_permissions.items():
            self.stdout.write(f'Setting up {role_name} role...')
            role, created = Role.objects.get_or_create(name=role_name)
            role.permissions.clear()  # Clear existing permissions

            if isinstance(role_config['models'], list):
                # For roles with full permissions on all specified models
                models = role_config['models']
                perms = role_config['permissions']
                for model_name in models:
                    self.assign_model_permissions(role, model_name, perms)
            else:
                # For roles with specific permissions per model
                for model_name, permissions in role_config['models'].items():
                    self.assign_model_permissions(role, model_name, permissions)

            self.stdout.write(self.style.SUCCESS(f'Successfully set up {role_name} role'))

    def assign_model_permissions(self, role, model_name, permissions):
        """
        Assign specified permissions for a model to a role
        """
        try:
            # Get content type for the model
            if model_name == 'user':
                ct = ContentType.objects.get(app_label='auth', model='user')
            else:
                ct = ContentType.objects.get(app_label='hmsapp', model=model_name)

            # Get and assign permissions
            for permission in permissions:
                perm_name = f'{permission}_{model_name}'
                try:
                    perm = Permission.objects.get(codename=perm_name, content_type=ct)
                    role.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f'Permission {perm_name} does not exist for {model_name}'
                    ))

        except ContentType.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'Content type for {model_name} does not exist'
            )) 