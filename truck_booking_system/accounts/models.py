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
    
    # Profile fields
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], blank=True)
    
    # Fix reverse accessor clashes with auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='user',
    )
    
    def is_company(self):
        return self.role == self.ROLE_COMPANY

    def is_customer(self):
        return self.role == self.ROLE_CUSTOMER

    def is_driver(self):
        return self.role == self.ROLE_DRIVER

    def __str__(self):
        return f"{self.username} ({self.role})"
