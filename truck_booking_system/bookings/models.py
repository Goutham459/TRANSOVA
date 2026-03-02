from django.db import models
from fleet.models import Truck
from pricing.models import LoadType
from django.conf import settings

class Booking(models.Model):
        user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True
    )
        customer_name = models.CharField(max_length=100)
        contact_number = models.CharField(max_length=10, default="0000000000")  # new field for phone
        pickup_location = models.CharField(max_length=200)
        drop_location = models.CharField(max_length=200)
        booking_date = models.DateField()
    
        distance_km = models.FloatField(default=0)
        price = models.FloatField(default=0)  # final price including commission
    
        truck = models.ForeignKey(
        Truck,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

        load_type = models.ForeignKey(
        LoadType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

        currency = models.CharField(max_length=10, default="USD")  # auto-detected currency

        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return f"{self.customer_name} - {self.booking_date}"

        def calculate_price(self, base_rate_per_km=2):
            """
            Calculate total price based on distance and 5% admin commission.
            """
            total = self.distance_km * base_rate_per_km
            total_with_commission = total * 1.05  # adding 5% commission
            self.price = round(total_with_commission, 2)
            return self.price