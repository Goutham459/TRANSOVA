#!/usr/bin/env python
"""
Script to check users in the database and prepare for migration to Render
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'truck_booking_system'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

print("=" * 50)
print("CURRENT DATABASE USER COUNT")
print("=" * 50)
print(f"Total Users: {User.objects.count()}")
print(f"Admins: {User.objects.filter(role='ADMIN').count()}")
print(f"Companies: {User.objects.filter(role='COMPANY').count()}")
print(f"Customers: {User.objects.filter(role='CUSTOMER').count()}")
print(f"Drivers: {User.objects.filter(role='DRIVER').count()}")
print("=" * 50)

# List all users
print("\nAll Users:")
print("-" * 50)
for user in User.objects.all().values('username', 'email', 'role', 'is_active'):
    print(f"  {user['username']} | {user['email']} | {user['role']} | Active: {user['is_active']}")

