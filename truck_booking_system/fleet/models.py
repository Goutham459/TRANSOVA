from django.db import models
from accounts.models import User
from django.conf import settings


class Company(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_profile"
    )
    company_name = models.CharField(max_length=255)
    trade_license = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.company_name

class Truck(models.Model):
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
        blank=True
    )
    truck_number = models.CharField(max_length=50)
    truck_type = models.CharField(max_length=50, choices=TRUCK_TYPES)
    capacity = models.FloatField()
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='truck_images/', blank=True, null=True)
    price_per_km = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def __str__(self):
        return self.truck_number
    
class Driver(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="drivers"
    )

    def __str__(self):
        return self.user.username
