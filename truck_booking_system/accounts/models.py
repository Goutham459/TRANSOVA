from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_ADMIN = "ADMIN"
    ROLE_COMPANY = "COMPANY"
    ROLE_CUSTOMER = "CUSTOMER"
    ROLE_DRIVER = "DRIVER"

    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_COMPANY, "Company"),
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_DRIVER, "Driver"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CUSTOMER
    )

    def is_company(self):
        return self.role == self.ROLE_COMPANY

    def is_customer(self):
        return self.role == self.ROLE_CUSTOMER

    def is_driver(self):
        return self.role == self.ROLE_DRIVER

    def __str__(self):
        return f"{self.username} ({self.role})"