from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Lists all superusers in the system'

    def handle(self, *args, **kwargs):
        superusers = User.objects.filter(is_superuser=True)
        
        if not superusers:
            self.stdout.write(self.style.WARNING('No superusers found in the system'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Found {superusers.count()} superuser(s):'))
        for user in superusers:
            self.stdout.write(f'Username: {user.username}')
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'Date joined: {user.date_joined}')
            self.stdout.write('---') 