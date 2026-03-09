
"""
Django Settings for Transova Truck Booking System.
===================================================
This configuration file contains all settings for the application.
For production, ensure to set environment variables or a .env file.
"""

import os
from pathlib import Path
from decouple import config  # pip install python-decouple for environment variables
import dj_database_url  # pip install dj-database-url for production database

# ============================================================================
# BASE CONFIGURATION
# ============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key in a secure location!
# In production, use: SECRET_KEY = config('SECRET_KEY')
SECRET_KEY = config('SECRET_KEY', default='django-insecure-i+ip@qxf13u3l*-j79y7e!rg2$4q0)_+#bda$+ixlrk7hy52j-')

# Debug mode - Set to False in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Allowed hosts - Comma-separated list of domain names
# In production: ALLOWED_HOSTS = ['transova.com', 'www.transova.com']
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    # Django
    # 'django.contrib.admin',  # Removed - using custom admin
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Custom apps (USER APP MUST COME FIRST)
    'accounts',
    'bookings',
    'fleet',
    'pricing',
]

# Authentication backends - Custom username backend
AUTHENTICATION_BACKENDS = [
    "accounts.backends.UsernameBackend",  # Custom username backend
    "django.contrib.auth.backends.ModelBackend",  # default
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# URLs
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'truck_booking_system.config.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
    BASE_DIR / "templates",
    BASE_DIR / "accounts" / "templates",
    BASE_DIR / "bookings" / "templates",
    BASE_DIR / "fleet" / "templates",
    BASE_DIR / "pricing" / "templates",  # inside the list
],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'bookings.context_processors.pending_companies_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'truck_booking_system.config.wsgi.application'

# Database
# For production (Render): Use dj-database-url with PostgreSQL
# In production, set DATABASE_URL environment variable
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JS, default images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# WhiteNoise storage for compressed static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# Directory where collectstatic will gather static files for deployment

# Media files (uploaded images)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email setup
# For development: Use console backend to see emails in terminal
# For production: Use smtp.EmailBackend with proper credentials
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Gmail SMTP settings (configured for OTP sending)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "gouthamkrishna106@gmail.com"
EMAIL_HOST_PASSWORD = "iyhj vtcg vmye qktp"
DEFAULT_FROM_EMAIL = "noreply@transova.com"
# ============================================================================
# PRICING CONFIGURATION
# ============================================================================
# These settings control the pricing logic for bookings.
# Base rate is charged per kilometer, with optional load type multipliers.

# BASE_PRICE: Minimum fixed charge for any booking (covers operational costs)
BASE_PRICE = 50  # Minimum booking charge in USD

# RATE_PER_KM: Price charged per kilometer traveled
RATE_PER_KM = 10  # Price per kilometer in USD

# BASE_RATE_CUSTOMER: Base rate for customer bookings (used in customer_booking)
BASE_RATE_CUSTOMER = 2  # Price per kilometer for customer-facing bookings

# COMMISSION_RATE: Admin/platform commission percentage (e.g., 0.05 = 5%)
COMMISSION_RATE = 0.05  # 5% platform commission

# These values can be overridden using environment variables:
# EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# ============================================================================
# CURRENCY SETTINGS
# ============================================================================
DEFAULT_CURRENCY = 'USD'  # Default currency code

# Currency API fallback - used to detect user's currency based on IP
CURRENCY_API_URL = 'https://ipapi.co/json/'

# ============================================================================
# PAGINATION SETTINGS
# ============================================================================
# Number of items to display per page in list views
ITEMS_PER_PAGE = 10  # Default pagination size
ADMIN_ITEMS_PER_PAGE = 20  # Items per page in admin panels

# ============================================================================
# SESSION SETTINGS
# ============================================================================
# Session key prefix for OTP and registration data
SESSION_OTP_KEY = 'otp'  # Key for storing OTP in session
SESSION_REG_DATA_KEY = 'reg_data'  # Key for storing registration data
SESSION_RESET_OTP_KEY = 'reset_otp'  # Key for password reset OTP
SESSION_RESET_EMAIL_KEY = 'reset_email'  # Key for password reset email

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
# CSRF and Session cookie settings
CSRF_COOKIE_HTTPONLY = True  # Prevent XSS attacks on cookies
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cross-site requests for ngrok
SESSION_COOKIE_HTTPONLY = True  # Prevent session theft via JS
SESSION_COOKIE_SAMESITE = 'Lax'  # Allow cross-site cookies for ngrok
SECURE_BROWSER_XSS_FILTER = True  # Enable XSS filter

# CSRF Trusted Origins - Required for ngrok and external access
# Add your ngrok URLs here or use environment variable
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', 
    default='https://transova.onrender.com,http://localhost:8000,http://127.0.0.1:8000').split(',')

# Use X-Forwarded-Host for proper host detection behind proxies/ngrok
USE_X_FORWARDED_HOST = True

# Password reset OTP validity (in minutes)
OTP_VALIDITY_MINUTES = 10

# ============================================================================
# BOOKING STATUS MAPPINGS
# ============================================================================
# These define the valid status values for bookings
BOOKING_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('IN_PROGRESS', 'In Progress'),
    ('COMPLETED', 'Completed'),
]

DRIVER_STATUS_CHOICES = [
    ('PENDING', 'Pending Assignment'),
    ('ASSIGNED', 'Driver Assigned'),
    ('ACCEPTED', 'Accepted'),
    ('REJECTED', 'Rejected'),
]

PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('PAID', 'Paid'),
    ('FAILED', 'Failed'),
    ('REFUNDED', 'Refunded'),
]
