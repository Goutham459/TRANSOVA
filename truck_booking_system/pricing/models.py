from django.db import models
from fleet.models import Company

class LoadType(models.Model):
    name = models.CharField(max_length=100)
    price_multiplier = models.FloatField(
        help_text="Example: Sand=1.0, Cement=1.3, Steel=1.5"
    )

    def __str__(self):
        return self.name

class Subscription(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)