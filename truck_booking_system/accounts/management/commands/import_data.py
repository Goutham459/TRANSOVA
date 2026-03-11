"""
Custom management command to load initial data during deployment.
This runs loaddata after migrations are complete.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = 'Load data from database_backup.json if database is empty'

    def handle(self, *args, **options):
        from accounts.models import User
        
        # Check if there are already users in the database
        if User.objects.exists():
            self.stdout.write(self.style.WARNING('Database already has users, skipping data import'))
            return
        
        # Path to backup file - check multiple locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database_backup.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'database_backup.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'truck_booking_system', 'database_backup.json'),
            '/app/database_backup.json',
            '/app/truck_booking_system/database_backup.json',
            'database_backup.json',
        ]
        
        backup_file = None
        for path in possible_paths:
            if os.path.exists(path):
                backup_file = path
                break
        
        if backup_file:
            try:
                self.stdout.write(f'Loading data from {backup_file}...')
                call_command('loaddata', backup_file)
                self.stdout.write(self.style.SUCCESS('Data imported successfully!'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error importing data: {e}'))
        else:
            self.stdout.write(self.style.WARNING('database_backup.json not found, skipping data import'))

