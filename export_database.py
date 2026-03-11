#!/usr/bin/env python
"""
Script to export Django database to JSON for migration to Render
"""
import os
import sys
import json
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'truck_booking_system'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Now do full export using Django's dumpdata
from io import StringIO
from django.core.management import call_command

output = StringIO()
call_command(
    'dumpdata',
    '--natural-foreign',
    '--natural-primary',
    '-e', 'contenttypes',
    '-e', 'auth.permission',
    '--indent', '2',
    stdout=output
)

# Write to file
output.seek(0)
content = output.read()

# Count items
data = json.loads(content)
print(f"Exported {len(data)} records")

with open('database_backup.json', 'w') as f:
    f.write(content)

print("\n" + "="*50)
print("Database exported successfully!")
print("File: database_backup.json")
print("="*50)

