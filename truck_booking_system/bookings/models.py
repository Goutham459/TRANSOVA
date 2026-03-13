from decimal import Decimal

from django.conf import settings
from django.db import models


class Booking(models.Model):
    """
    Core Booking Model - Main entity for truck bookings.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    DRIVER_STATUS_CHOICES = [
        ("", "No Driver"),
        ("ASSIGNED", "Assigned"),
        ("ACCEPTED", "Accepted"),
        ("REJECTED", "Rejected"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
    ]

    customer_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15, blank=True)
    pickup_location = models.CharField(max_length=200)
    drop_location = models.CharField(max_length=200)
    pickup_lat = models.FloatField(null=True, blank=True)
    pickup_lng = models.FloatField(null=True, blank=True)
    drop_lat = models.FloatField(null=True, blank=True)
    drop_lng = models.FloatField(null=True, blank=True)
    booking_date = models.DateField()
    distance_km = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="USD")
    truck = models.ForeignKey(
        "fleet.Truck",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    driver = models.ForeignKey(
        "fleet.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    load_type = models.ForeignKey(
        "pricing.LoadType", on_delete=models.SET_NULL, null=True, blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    driver_status = models.CharField(
        max_length=20, choices=DRIVER_STATUS_CHOICES, default="", blank=True
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="PENDING"
    )
    assigned_by_company = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["driver_status"]),
            models.Index(fields=["booking_date"]),
        ]

    def __str__(self):
        return f"Booking #{self.id} - {self.customer_name} ({self.status})"


class Payment(models.Model):
    """
    Payment Model - Records all payments for bookings.
    """

    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    payment_method = models.CharField(max_length=20, default="CARD")
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="PENDING"
    )
    transaction_id = models.CharField(max_length=100, unique=True, blank=True)
    card_last_four = models.CharField(max_length=4, blank=True, default="")
    card_type = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.transaction_id[:8]} - {self.amount} {self.currency}"


class Bid(models.Model):
    """
    Bid Model - Company bids on customer bookings.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("REJECTED", "Rejected"),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="bids")
    company = models.ForeignKey(
        "fleet.Company", on_delete=models.CASCADE, related_name="bids"
    )
    truck = models.ForeignKey(
        "fleet.Truck", on_delete=models.CASCADE, related_name="bids"
    )
    driver = models.ForeignKey(
        "fleet.Driver",
        on_delete=models.CASCADE,
        related_name="bids",
        null=True,
        blank=True,
    )
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("booking", "company")]
        ordering = ["bid_amount", "-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"Bid on #{self.booking.id} - {self.bid_amount} by {self.company}"


class ProofOfDelivery(models.Model):
    """
    ProofOfDelivery Model - Driver uploads delivery confirmation.
    """

    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="proof"
    )
    delivery_photo = models.ImageField(
        upload_to="delivery_photos/", blank=True, null=True
    )
    signature_image = models.ImageField(
        upload_to="delivery_signatures/", blank=True, null=True
    )
    received_by = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    delivered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Proof for Booking #{self.booking.id}"


class FAQQuestion(models.Model):
    """
    FAQQuestion Model - User questions and admin answers.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ANSWERED", "Answered"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    question = models.TextField()
    answer = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    is_public = models.BooleanField(default=False)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faq_replies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "is_public"])]

    def __str__(self):
        return f"Q: {self.subject} ({self.status})"


class CompanyRating(models.Model):
    """
    CompanyRating Model - Customer ratings for companies after completed bookings.
    """

    company = models.ForeignKey(
        "fleet.Company", on_delete=models.CASCADE, related_name="ratings"
    )
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="company_ratings"
    )
    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)], default=5
    )  # 1-5 stars
    comment = models.TextField(blank=True, max_length=500)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("company", "booking")]  # One rating per booking
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return f"{self.company.company_name}: {self.rating}/5 stars (Booking #{self.booking.id})"
