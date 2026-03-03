"""
================================================================================
FLEET MODELS
================================================================================
This module contains the Company, Truck, and Driver models for the Transova system.

Models:
    - Company: Represents a trucking company
    - Truck: Represents a truck in the fleet
    - Driver: Represents a driver employed by a company

Database Indexes:
    - is_available: For finding available trucks/drivers
    - company: For company-specific queries
    - is_approved: For company approval queries
================================================================================
"""

from django.db import models
from django.conf import settings


class Company(models.Model):
    """
    Company Model - Represents a trucking/transportation company.
    
    This model stores information about companies that own trucks
    and employ drivers. Companies require admin approval before
    they can operate on the platform.
    
    Fields:
        - user: Associated user account
        - company_name: Business name
        - trade_license: License number
        - contact information
        - is_approved: Admin approval status
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_profile"
    )
    
    company_name = models.CharField(max_length=255)
    trade_license = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    
    # Approval status - requires admin approval before company can operate
    is_approved = models.BooleanField(default=False, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        """Meta options for Company model."""
        ordering = ['-created_at']
        verbose_name_plural = "Companies"
    
    def __str__(self):
        status = "Approved" if self.is_approved else "Pending"
        return f"{self.company_name} ({status})"
    
    @property
    def is_active(self):
        """Check if company is approved and active."""
        return self.is_approved


class Truck(models.Model):
    """
    Truck Model - Represents a truck in a company's fleet.
    
    Stores information about trucks including:
    - Identification (truck number)
    - Type and capacity
    - Availability status
    - Pricing
    
    Common Queries (optimized with indexes):
        - Find available trucks
        - Get trucks by company
        - Filter by truck type
    """
    
    # Truck type choices
    TRUCK_TYPES = [
        ('box_truck', 'Box Truck'),
        ('flatbed', 'Flatbed'),
        ('refrigerated', 'Refrigerated Truck'),
        ('tanker', 'Tanker Truck'),
        ('semi_trailer', 'Semi-Trailer Truck (18-Wheeler)'),
        ('garbage', 'Garbage Truck'),
        ('car_carrier', 'Car Carrier Truck'),
        ('heavy_haul', 'Heavy Haul Truck'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="trucks",
        null=True,
        blank=True,
        db_index=True  # Index for company-specific queries
    )
    
    truck_number = models.CharField(max_length=50)
    truck_type = models.CharField(max_length=50, choices=TRUCK_TYPES)
    capacity = models.FloatField()
    
    # Availability status - crucial for booking system
    is_available = models.BooleanField(default=True, db_index=True)
    
    image = models.ImageField(upload_to='truck_images/', blank=True, null=True)
    price_per_km = models.DecimalField(max_digits=8, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        """Meta options for Truck model."""
        ordering = ['-created_at']
        # Ensure truck numbers are unique within a company
        unique_together = [['company', 'truck_number']]
    
    def __str__(self):
        company_name = self.company.company_name if self.company else "No Company"
        return f"{self.truck_number} - {self.get_truck_type_display()} ({company_name})"
    
    @property
    def is_available_for_booking(self):
        """Check if truck can be booked."""
        return self.is_available


class Driver(models.Model):
    """
    Driver Model - Represents a driver employed by a company.
    
    Stores driver information including:
    - User account association
    - Company employment
    - License information
    - Availability status
    - Assigned truck (optional)
    
    Common Queries (optimized with indexes):
        - Find available drivers
        - Get drivers by company
        - Find driver by user
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
        null=True,
        blank=True,
        db_index=True  # Index for user lookup
    )
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="drivers",
        db_index=True  # Index for company-specific queries
    )
    
    # License information
    license_number = models.CharField(max_length=50, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Profile
    profile_picture = models.ImageField(upload_to='driver_photos/', blank=True, null=True)
    experience_years = models.IntegerField(default=0)
    
    # Availability - determines if driver can be assigned jobs
    is_available = models.BooleanField(default=True, db_index=True)
    
    # Link driver to a truck (optional assignment)
    assigned_truck = models.ForeignKey(
        'Truck',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_drivers"
    )
    
    class Meta:
        """Meta options for Driver model."""
        ordering = ['-created_at'] if hasattr(models.Model, 'created_at') else ['user__username']
    
    def __str__(self):
        username = self.user.username if self.user else "No User"
        company_name = self.company.company_name if self.company else "No Company"
        return f"{username} ({company_name})"
    
    @property
    def full_name(self):
        """Get driver's full name."""
        if self.user:
            return self.user.get_full_name() or self.user.username
        return "Unknown"
    
    @property
    def is_licensed(self):
        """Check if driver has valid license."""
        if not self.license_number:
            return False
        if self.license_expiry and self.license_expiry < models.DateField().default:
            return False
        return True

