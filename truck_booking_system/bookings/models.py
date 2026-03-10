"""
================================================================================
BOOKINGS MODELS
================================================================================
This module contains the Booking and Payment models for the Transova system.

Models:
    - Booking: Represents a truck booking/order
    - Payment: Represents payment for a booking

Database Indexes:
    - booking_date: For date-based queries
    - status: For filtering by status
    - truck: For truck-specific bookings
    - user: For user-specific bookings
    - created_at: For sorting and time-based queries
================================================================================
"""

from django.db import models
from django.conf import settings
import uuid


class Booking(models.Model):
    """
    Booking Model - Represents a truck booking/order in the system.
    
    This model stores all information about a booking including:
    - Customer information
    - Pickup and drop locations (with GPS coordinates)
    - Distance and pricing
    - Truck and driver assignments
    - Status tracking
    
    Common Queries (optimized with indexes):
        - Find bookings by date range
        - Filter by status (pending, in_progress, completed)
        - Get bookings for a specific truck
        - Get bookings for a specific customer
    """
    
    # Status choices for the booking lifecycle
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]
    
    # Payment status choices
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    # Driver assignment status choices
    DRIVER_STATUS_CHOICES = [
        ('PENDING', 'Pending Assignment'),
        ('ASSIGNED', 'Driver Assigned'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]
    
    # --------------------------------------------------------------------------
    # CUSTOMER INFORMATION
    # --------------------------------------------------------------------------
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
        db_index=True  # Index for user-specific bookings
    )
    
    customer_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=10, default="0000000000")
    
    # --------------------------------------------------------------------------
    # LOCATION INFORMATION
    # --------------------------------------------------------------------------
    pickup_location = models.CharField(max_length=200)
    drop_location = models.CharField(max_length=200)
    booking_date = models.DateField(db_index=True)  # Index for date queries
    
    # GPS coordinates for navigation (used for distance calculation)
    pickup_lat = models.FloatField(null=True, blank=True)
    pickup_lng = models.FloatField(null=True, blank=True)
    drop_lat = models.FloatField(null=True, blank=True)
    drop_lng = models.FloatField(null=True, blank=True)
    
    # --------------------------------------------------------------------------
    # PRICING INFORMATION
    # --------------------------------------------------------------------------
    distance_km = models.FloatField(default=0)
    price = models.FloatField(default=0)
    currency = models.CharField(max_length=10, default="USD")
    
    # --------------------------------------------------------------------------
    # STATUS FIELDS
    # --------------------------------------------------------------------------
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING',
        db_index=True  # Index for status filtering
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='PENDING'
    )
    driver_status = models.CharField(
        max_length=20,
        choices=DRIVER_STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    
    # --------------------------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------------------------
    truck = models.ForeignKey(
        'fleet.Truck',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        db_index=True  # Index for truck-specific bookings
    )
    
    # Track which driver handled this booking
    driver = models.ForeignKey(
        'fleet.Driver',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        db_index=True  # Index for driver-specific bookings
    )
    
    # Track if job was assigned by company (driver cannot reject/cancel)
    assigned_by_company = models.BooleanField(default=False)
    
    load_type = models.ForeignKey(
        'pricing.LoadType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Timestamp for driver assignment
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # --------------------------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  # Index for sorting
    
    class Meta:
        """
        Meta options for Booking model.
        
        Indexes:
            - booking_date: For date range queries
            - status: For status filtering
            - created_at: For recent bookings
            - Composite indexes for common query patterns
        """
        ordering = ['-booking_date', '-created_at']  # Default ordering
        indexes = [
            # Index for customer dashboard queries
            models.Index(fields=['customer_name', 'booking_date']),
            # Index for company booking queries
            models.Index(fields=['truck', 'status']),
            # Index for driver job queries
            models.Index(fields=['driver', 'status']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.booking_date}"
    
    def calculate_price(self, base_rate_per_km=2):
        """
        Calculate total price based on distance and 5% admin commission.
        
        Args:
            base_rate_per_km: Rate per kilometer (default: 2)
        
        Returns:
            float: Calculated price rounded to 2 decimal places
        """
        total = self.distance_km * base_rate_per_km
        total_with_commission = total * 1.05  # adding 5% commission
        self.price = round(total_with_commission, 2)
        return self.price
    
    @property
    def is_completed(self):
        """Check if booking is completed."""
        return self.status == 'COMPLETED'
    
    @property
    def is_paid(self):
        """Check if booking is paid."""
        return self.payment_status == 'PAID'


class Bid(models.Model):
    """
    Bid Model - Represents a company's bid on a booking/job.
    
    Allows companies to bid on available jobs posted by shippers.
    Shippers can then accept one of the bids.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]
    
    booking = models.ForeignKey(
        'Booking',
        on_delete=models.CASCADE,
        related_name='bids'
    )
    
    company = models.ForeignKey(
        'fleet.Company',
        on_delete=models.CASCADE,
        related_name='bids'
    )
    
    truck = models.ForeignKey(
        'fleet.Truck',
        on_delete=models.CASCADE,
        related_name='bids'
    )
    
    driver = models.ForeignKey(
        'fleet.Driver',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bids'
    )
    
    bid_amount = models.FloatField()
    estimated_pickup_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        # A company can only bid once per booking
        unique_together = [['booking', 'company']]
    
    def __str__(self):
        return f"Bid #{self.id} - {self.company.company_name} - {self.booking.id}"


class ProofOfDelivery(models.Model):
    """
    ProofOfDelivery Model - Stores proof of delivery for completed bookings.
    
    Drivers upload photos and signatures as proof of delivery.
    """
    
    booking = models.OneToOneField(
        'Booking',
        on_delete=models.CASCADE,
        related_name='proof_of_delivery'
    )
    
    # Photo proof
    delivery_photo = models.ImageField(
        upload_to='delivery_photos/',
        blank=True,
        null=True
    )
    
    # Signature
    signature_image = models.ImageField(
        upload_to='delivery_signatures/',
        blank=True,
        null=True
    )
    
    # Recipient name who received the delivery
    received_by = models.CharField(max_length=100, blank=True)
    
    # Delivery notes
    notes = models.TextField(blank=True)
    
    # Timestamp
    delivered_at = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"Proof of Delivery - Booking #{self.booking.id}"


class Payment(models.Model):
    """
    Payment Model - Represents payment for a booking.
    
    Stores payment transaction details including:
    - Amount and currency
    - Payment method
    - Transaction status
    - Card details (last 4 digits only for security)
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('CARD', 'Credit/Debit Card'),
        ('WALLET', 'Digital Wallet'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # One-to-one relationship with booking
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default='USD')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Transaction tracking
    transaction_id = models.CharField(
        max_length=100, 
        unique=True, 
        default=uuid.uuid4,
        db_index=True  # Index for transaction lookup
    )
    
    # Card details (masked for security)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)
    card_type = models.CharField(max_length=20, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        """Meta options for Payment model."""
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"
    
    @property
    def is_successful(self):
        """Check if payment was successful."""
        return self.status == 'SUCCESS'


class FAQQuestion(models.Model):
    """
    FAQQuestion Model - Stores user-submitted questions and admin replies.
    
    Allows users to submit questions through the FAQ page.
    Admins can view and reply to these questions.
    Users can view all answered questions publicly.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ANSWERED', 'Answered'),
    ]
    
    # User who submitted the question (optional - guests can also ask)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faq_questions'
    )
    
    # Contact email for guest users
    email = models.EmailField(blank=True)
    
    # The question subject
    subject = models.CharField(max_length=200)
    
    # The question details
    question = models.TextField()
    
    # Admin's reply
    answer = models.TextField(blank=True)
    
    # Who replied (admin user)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faq_replies'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    # Whether to show on FAQ page publicly
    is_public = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        """Meta options for FAQQuestion model."""
        ordering = ['-created_at']
    
    def __str__(self):
        return f"FAQ #{self.id} - {self.subject}"

