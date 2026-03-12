from django.db import models
from django.conf import settings
from decimal import Decimal


class LoadType(models.Model):
    name = models.CharField(max_length=100)
    price_multiplier = models.FloatField(
        help_text="Example: Sand=1.0, Cement=1.3, Steel=1.5"
    )
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Load Types"


class Subscription(models.Model):
    company = models.ForeignKey(
        'fleet.Company', 
        on_delete=models.CASCADE,
        db_index=True
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.company.company_name} - ${self.amount} ({status})"

    class Meta:
        ordering = ['-start_date']
        verbose_name_plural = "Subscriptions"

