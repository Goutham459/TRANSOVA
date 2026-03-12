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
from django.utils import timezone
from decimal import Decimal


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
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
    - GPS tracking for real-time location
    
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
    
    # Real-time GPS tracking fields
    current_latitude = models.FloatField(null=True, blank=True, db_index=True)
    current_longitude = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False, db_index=True)  # GPS device online status
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        """Meta options for Driver model."""
        ordering = ['-created_at']
    
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
        if self.license_expiry and self.license_expiry < timezone.now().date():
            return False
        return True


class Wallet(models.Model):
    """
    Wallet Model - Represents a company's wallet for earnings and payouts.
    
    Stores company's accumulated earnings from bookings.
    Payments are held in escrow until delivery is completed.
    """
    
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    
    # Balance fields
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    escrow_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Held in escrow
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid_out = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Bank details for payouts
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_holder = models.CharField(max_length=100, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wallet - {self.company.company_name}"
    
    @property
    def available_balance(self):
        """Balance available for payout (total - escrow)"""
        return self.balance - self.escrow_balance
    
    def add_earning(self, amount, booking=None, description=""):
        """Add earnings to wallet (from completed booking)"""
        self.balance += Decimal(str(amount))
        self.total_earned += Decimal(str(amount))
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            wallet=self,
            transaction_type='EARNING',
            amount=amount,
            booking=booking,
            description=description,
            status='COMPLETED'
        )
    
    def hold_in_escrow(self, amount, booking=None, description=""):
        """Hold amount in escrow (when payment is received)"""
        self.escrow_balance += Decimal(str(amount))
        self.save()
        
        Transaction.objects.create(
            wallet=self,
            transaction_type='ESCROW_HOLD',
            amount=amount,
            booking=booking,
            description=description,
            status='PENDING'
        )
    
    def release_from_escrow(self, amount, booking=None, description=""):
        """Release amount from escrow after delivery"""
        self.escrow_balance -= Decimal(str(amount))
        self.balance += Decimal(str(amount))
        self.save()
        
        Transaction.objects.create(
            wallet=self,
            transaction_type='ESCROW_RELEASE',
            amount=amount,
            booking=booking,
            description=description,
            status='COMPLETED'
        )
    
    def process_payout(self, amount, description=""):
        """Process payout to company's bank account"""
        if self.available_balance < Decimal(str(amount)):
            return False
        
        self.balance -= Decimal(str(amount))
        self.total_paid_out += Decimal(str(amount))
        self.save()
        
        Transaction.objects.create(
            wallet=self,
            transaction_type='PAYOUT',
            amount=amount,
            description=description,
            status='PROCESSING'
        )
        return True


class Transaction(models.Model):
    """
    Transaction Model - Ledger of all wallet transactions.
    
    Tracks all earnings, escrow holds, releases, and payouts.
    """
    
    TRANSACTION_TYPES = [
        ('ESCROW_HOLD', 'Escrow Hold'),
        ('ESCROW_RELEASE', 'Escrow Release'),
        ('EARNING', 'Earning'),
        ('PAYOUT', 'Payout'),
        ('REFUND', 'Refund'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions'
    )
    
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reference_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.status}"

