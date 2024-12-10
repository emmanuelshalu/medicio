from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction

class Command(BaseCommand):
    help = 'Initialize database with required data'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        # Create default groups
        groups = ['Administrators', 'Doctors', 'Staff']
        for group_name in groups:
            Group.objects.get_or_create(name=group_name)
            self.stdout.write(f'Created group: {group_name}')

        self.stdout.write(self.style.SUCCESS('Database initialization completed')) 