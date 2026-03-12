"""
================================================================================
BOOKINGS APPLICATION VIEWS
================================================================================
This module contains all view functions for the bookings application.

Views are organized into the following sections:
    1. Public Views (home, public booking, etc.)
    2. Customer Views (dashboard, booking, profile)
    3. Driver Views (dashboard, job management)
    4. Company Views (company dashboard, bookings)
    5. Admin Views (management panels)
    6. Authentication Views (login, register, OTP)
    7. Payment Views
    8. Utility Views (FAQ, calculator)

Each view includes:
    - Docstring explaining purpose and functionality
    - Permission checks
    - Error handling
    - Query optimizations with select_related/prefetch_related

For pricing logic, see: bookings/utils.py
For settings, see: config/settings.py
================================================================================
"""

# ============================================================================
# DJANGO CORE IMPORTS
# ============================================================================
import math
import logging
import random
import uuid
import requests
from typing import Optional, Any

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django import forms

# For PDF generation
from django.template.loader import render_to_string
from django.conf import settings
import io

# ============================================================================
# APPLICATION IMPORTS
# ============================================================================
from .models import Booking, Payment, Bid, ProofOfDelivery, FAQQuestion
from fleet.models import Truck, Company, Driver, Wallet, Transaction
from pricing.models import LoadType
from accounts.models import User

# Import utility functions from utils module
from .utils import (
    get_distance_haversine,
    calculate_booking_price,
    calculate_admin_booking_price,
    detect_user_currency,
    validate_booking_data,
    validate_coordinates,
    detect_card_type,
    mask_card_number,
    generate_otp,
    store_otp_in_session,
    validate_session_otp,
    format_price,
)

# ============================================================================
# LOGGER CONFIGURATION
# ============================================================================
# Logger for debugging and error tracking
logger = logging.getLogger(__name__)


# =============================================================================
# SECTION 1: PUBLIC VIEWS
# =============================================================================
# Public-facing views that don't require authentication

def home(request):
    """
    Home page view - displays available trucks and load types.
    
    This is the landing page showing available trucks for booking.
    Only shows trucks that are currently available for booking.
    
    URL: /
    Template: bookings/home.html
    
    Query Optimization:
        - Uses filter(is_available=True) to only show available trucks
        - LoadTypes are lightweight, fetched with all()
    """
    # Get all available trucks for booking
    # Only show trucks where is_available=True
    trucks = Truck.objects.filter(is_available=True)
    
    # Get all load types for the booking form
    load_types = LoadType.objects.all()
    
    # Dynamic stats for home page
    from fleet.models import Driver, Company
    total_bookings = Booking.objects.count()
    available_trucks_count = trucks.count()
    total_load_types = load_types.count()
    total_drivers = Driver.objects.count()
    total_companies = Company.objects.filter(is_approved=True).count()
    
    context = {
        'trucks': trucks,
        'load_types': load_types,
        'stats': {
            'total_bookings': total_bookings,
            'available_trucks': available_trucks_count,
            'total_drivers': total_drivers,
            'total_companies': total_companies,
            'load_types_count': total_load_types,
        }
    }
    
    return render(request, "bookings/home.html", context)


def booking_list(request):
    """
    Admin booking list view - shows all bookings in the system.
    
    URL: /list/
    Template: bookings/booking_list.html
    
    Access: Admin users only (is_staff, is_superuser, or role='ADMIN')
    """
    # Check admin access
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    # Order by most recent booking first
    bookings = Booking.objects.all().select_related('truck', 'user', 'load_type').order_by("-booking_date")
    
    # Calculate statistics
    total_bookings = bookings.count()
    confirmed_count = bookings.filter(truck__isnull=False).count()
    pending_count = bookings.filter(truck__isnull=True).count()
    total_revenue = bookings.aggregate(Sum("price"))["price__sum"] or 0
    
    return render(request, "bookings/booking_list.html", {
        "bookings": bookings,
        "total_bookings": total_bookings,
        "confirmed_count": confirmed_count,
        "pending_count": pending_count,
        "total_revenue": total_revenue
    })


def add_booking(request):
    """
    Add new booking view (admin/internal use).
    
    This is the admin-facing booking creation form.
    For customer bookings, see customer_booking() view.
    
    URL: /add/
    Template: bookings/add_booking.html
    
    Pricing Logic:
        Uses calculate_admin_booking_price() from utils:
        (BASE_PRICE + distance_km * RATE_PER_KM) * load_multiplier
    
    Settings Used:
        - BASE_PRICE: 50 (minimum fixed charge)
        - RATE_PER_KM: 10 (price per kilometer)
    """
    # Get all trucks and load types for the form
    trucks = Truck.objects.all()
    load_types = LoadType.objects.all()

    if request.method == "POST":
        # Get form data
        truck = Truck.objects.get(id=request.POST.get("truck"))
        load_type = LoadType.objects.get(id=request.POST.get("load_type"))
        distance_km = float(request.POST.get("distance_km"))

        # Calculate price using centralized pricing function
        # Formula: (BASE_PRICE + distance * RATE_PER_KM) * load_multiplier
        price = calculate_admin_booking_price(
            distance_km=distance_km,
            load_multiplier=load_type.price_multiplier
        )

        # Create the booking
        Booking.objects.create(
            customer_name=request.POST.get("customer_name"),
            pickup_location=request.POST.get("pickup_location"),
            drop_location=request.POST.get("drop_location"),
            booking_date=request.POST.get("booking_date"),
            distance_km=distance_km,
            truck=truck,
            load_type=load_type,
            price=price
        )

        # Mark truck as unavailable
        truck.is_available = False
        truck.save()

        messages.success(request, "Booking created successfully!")
        return redirect("add_booking")

    return render(request, "bookings/add_booking.html", {
        "trucks": trucks,
        "load_types": load_types
    })



@login_required(login_url='/login/')
def edit_booking(request, booking_id):
    """
    Customer: Edit booking_date ONLY for PENDING bookings (before company approval).
    Admin/Staff: Full edit access (all fields).
    
    URL: /edit/<booking_id>/
    Template: bookings/edit_booking.html
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # CUSTOMER MODE: Date-only for PENDING bookings
    if request.user.role == 'CUSTOMER':
        # Verify ownership (matches customer_booking_list logic)
        if not (booking.customer_name == request.user.get_full_name() or 
                booking.customer_name == request.user.username or 
                booking.user == request.user):
            messages.error(request, "You can only edit your own bookings.")
            return redirect('customer_booking_list')
        
        # PENDING only (truck__isnull=True = before company approval)
        if booking.truck:
            messages.error(request, "Cannot edit confirmed bookings (truck assigned by company).")
            return redirect('customer_booking_list')
        
        # DATE ONLY updates for customers
        if request.method == "POST":
            new_date = request.POST.get("booking_date")
            if new_date:
                booking.booking_date = new_date
                booking.save()
                messages.success(request, "Booking date updated successfully!")
            else:
                messages.error(request, "Please select a new date.")
            return redirect('customer_booking_list')
        
        # Render customer template (date picker only)
        return render(request, "bookings/edit_booking.html", {
            "booking": booking,
            "customer_mode": True  # Template flag for simplified form
        })
    
    # ADMIN/STAFF MODE: Full edit access (existing logic preserved)
    # Admin check
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "Admin access required for full edits.")
        return redirect('booking_list')
    
    # Get available trucks + current booking's truck
    trucks = Truck.objects.filter(is_available=True) | Truck.objects.filter(id=booking.truck.id) if booking.truck else Truck.objects.filter(is_available=True)
    load_types = LoadType.objects.all()

    if request.method == "POST":
        booking.customer_name = request.POST.get("customer_name", booking.customer_name)
        booking.pickup_location = request.POST.get("pickup_location", booking.pickup_location)
        booking.drop_location = request.POST.get("drop_location", booking.drop_location)
        booking.booking_date = request.POST.get("booking_date", booking.booking_date)
        booking.distance_km = float(request.POST.get("distance_km", booking.distance_km))

        truck_id = request.POST.get("truck")
        if truck_id:
            booking.truck = Truck.objects.get(id=truck_id)
        
        load_type_id = request.POST.get("load_type")
        if load_type_id:
            booking.load_type = LoadType.objects.get(id=load_type_id)

        # Recalculate price using centralized function (admin only)
        if booking.load_type:
            booking.price = calculate_admin_booking_price(
                distance_km=booking.distance_km,
                load_multiplier=booking.load_type.price_multiplier
            )

        booking.save()
        messages.success(request, "Booking updated successfully!")
        return redirect("booking_list")

    return render(request, "bookings/edit_booking.html", {
        "booking": booking,
        "trucks": trucks,
        "load_types": load_types,
        "customer_mode": False  # Full admin form
    })



def delete_booking(request, booking_id):
    """
    Delete a booking and release the associated truck.
    
    URL: /delete/<booking_id>/
    
    When a booking is deleted:
        1. The associated truck becomes available again
        2. The booking record is removed from database
    """
    booking = get_object_or_404(Booking, id=booking_id)
    truck = booking.truck
    booking.delete()

    # Release the truck back to available status
    if truck:
        truck.is_available = True
        truck.save()

    messages.success(request, "Booking deleted successfully!")
    return redirect("booking_list")


def trucks_list(request):
    """
    Public truck listing with filtering options.
    
    URL: /trucks/
    Template: bookings/trucks_list.html
    
    Filters:
        - type: Filter by truck type
        - load: Filter by supported load type
        - availability: Filter by availability status
    
    Query Optimization:
        - Uses values_list for distinct truck types
    """
    trucks = Truck.objects.all()

    # Filter by truck type
    if request.GET.get("type"):
        trucks = trucks.filter(truck_type__iexact=request.GET["type"])

    # Filter by load type
    if request.GET.get("load"):
        trucks = trucks.filter(load_types__id=request.GET["load"])

    # Filter by availability
    if request.GET.get("availability") == "available":
        trucks = trucks.filter(is_available=True)
    elif request.GET.get("availability") == "booked":
        trucks = trucks.filter(is_available=False)

    context = {
        "trucks": trucks,
        "load_types": LoadType.objects.all(),
        "truck_types": Truck.objects.values_list("truck_type", flat=True).distinct(),
        "selected_type": request.GET.get("type"),
        "selected_load": request.GET.get("load"),
        "selected_availability": request.GET.get("availability"),
    }
    
    return render(request, "bookings/trucks_list.html", context)


# =============================================================================
# SECTION 2: CUSTOMER VIEWS
# =============================================================================
# Views for authenticated customers

@login_required(login_url='/login/')
def customer_dashboard(request):
    """
    Customer dashboard - shows booking history and statistics.
    
    URL: /customer-dashboard/
    Template: bookings/customer_dashboard.html
    
    Displays:
        - Total number of bookings
        - Confirmed vs pending bookings
        - Total amount spent
        - Recent bookings (last 10)
    
    Query Optimization:
        - Single query with filter, reused for multiple aggregations
        - Slicing applied AFTER aggregation
    """
    # Verify user is a customer
    if request.user.role != 'CUSTOMER':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    # Get bookings for this customer
    # Use OR query to match either full name or username
    user_bookings = Booking.objects.filter(
        Q(customer_name=request.user.get_full_name()) | 
        Q(customer_name=request.user.username)
    ).order_by("-booking_date")
    
    # Calculate statistics using efficient aggregation
    confirmed_bookings = user_bookings.filter(truck__isnull=False).count()
    pending_bookings = user_bookings.filter(truck__isnull=True).count()
    total_spent = user_bookings.aggregate(Sum("price"))["price__sum"] or 0
    
    # Pass ALL filtered bookings with status info for dashboard table
    all_customer_bookings = user_bookings.select_related('truck', 'load_type')
    
    context = {
        'bookings': all_customer_bookings,
        'total_bookings': user_bookings.count(),
        'confirmed_bookings': confirmed_bookings,
        'pending_bookings': pending_bookings,
        'total_spent': total_spent,
    }
    return render(request, "bookings/customer_dashboard.html", context)


@login_required(login_url='/login/')
def customer_booking(request):
    """
    Customer booking form with AJAX support for real-time pricing.
    
    URL: /book/
    Template: bookings/customer_booking.html
    
    Features:
        - AJAX submission for real-time price calculation
        - Automatic distance calculation using GPS coordinates
        - Currency detection based on user IP
        - Price calculation with commission
    
    Pricing Logic:
        Uses calculate_booking_price():
        (distance_km * BASE_RATE) * (1 + COMMISSION_RATE)
    
    AJAX Response:
        Returns JSON with:
        - success: Boolean
        - amount: Calculated price
        - currency: Detected currency
        - booking_id: Created booking ID
    """
    # Check for AJAX request
    # Note: request.is_ajax() deprecated in Django 3.1, using header instead
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    # Require authentication for booking
    if is_ajax and not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'}, status=401)
    
    # Get available trucks and load types
    trucks = Truck.objects.filter(is_available=True)
    load_types = LoadType.objects.all()

    # Handle AJAX POST request for booking creation
    if request.method == "POST" and is_ajax:
        # Extract form data
        customer_name = request.POST.get("customer_name")
        contact_number = request.POST.get("contact_number")
        pickup_location = request.POST.get("pickup_location")
        drop_location = request.POST.get("drop_location")
        booking_date = request.POST.get("booking_date")

        # Get GPS coordinates
        pickup_lat = float(request.POST.get("pickup_lat"))
        pickup_lng = float(request.POST.get("pickup_lng"))
        drop_lat = float(request.POST.get("drop_lat"))
        drop_lng = float(request.POST.get("drop_lng"))

        # Calculate distance using Haversine formula
        distance_km = get_distance_haversine(pickup_lat, pickup_lng, drop_lat, drop_lng)

        # Get load type multiplier
        load_type_id = request.POST.get("load_type")
        load_multiplier = 1.0
        if load_type_id:
            try:
                load_type = LoadType.objects.get(id=load_type_id)
                load_multiplier = load_type.price_multiplier
            except LoadType.DoesNotExist:
                pass

        # Calculate price with commission using centralized function
        price = calculate_booking_price(
            distance_km=distance_km,
            load_multiplier=load_multiplier,
            include_commission=True
        )

        # Detect user's currency based on IP
        currency = detect_user_currency()

        # Assign first available truck
        truck = trucks.first() if trucks.exists() else None
        if truck:
            truck.is_available = False
            truck.save()

        # Get selected load type
        load_type = None
        if load_type_id:
            load_type = LoadType.objects.filter(id=load_type_id).first()

        # Create booking
        booking = Booking.objects.create(
            customer_name=customer_name,
            contact_number=contact_number,
            pickup_location=pickup_location,
            drop_location=drop_location,
            booking_date=booking_date,
            distance_km=distance_km,
            price=price,
            currency=currency,
            truck=truck,
            load_type=load_type,
            user=request.user  # Associate with logged-in user
        )

        return JsonResponse({
            "success": True,
            "amount": price,
            "currency": currency,
            "booking_id": booking.id
        })

    # GET request - show the booking form
    # Check if a truck is selected via query parameter
    selected_truck = None
    selected_truck_id = request.GET.get('truck')
    if selected_truck_id:
        selected_truck = Truck.objects.filter(id=selected_truck_id).first()
    
    return render(request, "bookings/customer_booking.html", {
        "trucks": trucks,
        "load_types": load_types,
        "selected_truck": selected_truck,
    })


@login_required(login_url='/login/')
def customer_booking_list(request):
    """
    Enhanced customer booking list with search and filters.
    
    URL: /bookings/my-bookings/
    Template: bookings/customer_booking_list.html
    
    Filters:
        - search: Search by pickup/drop location or booking ID
        - status: Filter by confirmed/pending
        - from_date / to_date: Date range filter
    
    Query Optimization:
        - Uses Q objects for complex queries
        - Applies filters efficiently
    """
    if request.user.role != 'CUSTOMER':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    # Get base queryset - filter by user, customer name, or username
    bookings = Booking.objects.filter(
        Q(user=request.user) |
        Q(customer_name=request.user.get_full_name()) | 
        Q(customer_name=request.user.username)
    ).order_by("-booking_date")
    
    # Apply search filter
    search_query = request.GET.get('search', '')
    if search_query:
        bookings = bookings.filter(
            Q(pickup_location__icontains=search_query) |
            Q(drop_location__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Apply status filter
    status_filter = request.GET.get('status', '')
    if status_filter == 'confirmed':
        bookings = bookings.filter(truck__isnull=False)
    elif status_filter == 'pending':
        bookings = bookings.filter(truck__isnull=True)
    
    # Apply date filters
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    if from_date:
        bookings = bookings.filter(booking_date__gte=from_date)
    if to_date:
        bookings = bookings.filter(booking_date__lte=to_date)
    
    context = {
        'bookings': bookings,
        'search_query': search_query,
        'status_filter': status_filter,
        'from_date': from_date,
        'to_date': to_date,
    }
    return render(request, "bookings/customer_booking_list.html", context)


@login_required(login_url='/login/')
def profile(request):
    """
    Customer profile view with booking history.
    
    URL: /profile/
    Template: bookings/profile.html
    
    Displays:
        - User profile information
        - Recent bookings (last 5)
        - Quick stats
    
    Access: Authenticated customers only
    """
    if request.user.role != 'CUSTOMER':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    # Get bookings for this customer
    user_bookings = Booking.objects.filter(
        Q(customer_name=request.user.get_full_name()) | 
        Q(customer_name=request.user.username) |
        Q(user=request.user)
    ).order_by("-booking_date")
    
    # Get recent bookings for display
    recent_bookings = user_bookings[:5]
    
    # Calculate statistics
    total_bookings = user_bookings.count()
    confirmed_bookings = user_bookings.filter(truck__isnull=False).count()
    pending_bookings = user_bookings.filter(truck__isnull=True).count()
    total_spent = user_bookings.aggregate(Sum("price"))["price__sum"] or 0
    
    context = {
        'user': request.user,
        'bookings': recent_bookings,
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'pending_bookings': pending_bookings,
        'total_spent': total_spent,
    }
    return render(request, "bookings/profile.html", context)


@login_required(login_url='/login/')
def booking_receipt(request, booking_id):
    """
    View booking receipt/invoice.
    
    URL: /bookings/receipt/<booking_id>/
    Template: bookings/booking_receipt.html
    
    Access Control:
        - Only the customer who made the booking can view
        - Admins can view any receipt
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify ownership
    if request.user.role == 'CUSTOMER':
        if booking.customer_name != request.user.get_full_name() and \
           booking.customer_name != request.user.username:
            if not request.user.is_staff:
                messages.error(request, "You are not authorized to view this receipt.")
                return redirect('customer_dashboard')
    
    return render(request, "bookings/booking_receipt.html", {"booking": booking})


@login_required(login_url='/login/')
def download_receipt_pdf(request, booking_id):
    """
    Download booking receipt as PDF.
    
    URL: /bookings/receipt/<booking_id>/download/
    
    Access Control:
        - Only the customer who made the booking can download
        - Admins can download any receipt
    """
    # Check if WeasyPrint is available and working
    weasyprint_available = False
    if not weasyprint_available:
        # Always fall back to HTML receipt (no PDF generation)
        # This is more reliable across different environments
        booking = get_object_or_404(Booking, id=booking_id)
        
        # Verify ownership
        if request.user.role == 'CUSTOMER':
            if booking.customer_name != request.user.get_full_name() and \
               booking.customer_name != request.user.username:
                if not request.user.is_staff:
                    messages.error(request, "You are not authorized to download this receipt.")
                    return redirect('customer_dashboard')
        
        messages.info(request, "PDF download is not available. Using browser print instead.")
        return render(request, "bookings/booking_receipt.html", {"booking": booking})


# =============================================================================
# SECTION 3: DRIVER VIEWS
# =============================================================================
# Views for drivers

@login_required(login_url='/login/')
def driver_dashboard(request):
    """
    Driver dashboard - shows assigned jobs and statistics.
    
    URL: /driver-dashboard/
    Template: bookings/dashboard.html (or driver-specific template)
    
    Displays:
        - Today's jobs
        - Pending jobs
        - Completed jobs
        - Weekly earnings
    
    Query Optimization:
        - Uses select_related for truck and user
        - Date filtering with timezone awareness
    """
    if request.user.role != 'DRIVER':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    # Get driver profile
    try:
        driver = Driver.objects.get(user=request.user)
    except Driver.DoesNotExist:
        driver = None
    
    if driver:
        # Get today's date with timezone
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # Get view type from query params
        view_type = request.GET.get('view', 'all')
        
        # Filter bookings based on view type
        if view_type == 'today':
            driver_bookings = Booking.objects.filter(
                driver=driver,
                booking_date=today
            ).select_related('truck', 'user', 'load_type').order_by('-booking_date')[:10]
        elif view_type == 'jobs':
            driver_bookings = Booking.objects.filter(
                driver=driver
            ).select_related('truck', 'user', 'load_type').order_by('-booking_date')[:20]
        else:
            # Default: Show pending/active jobs
            driver_bookings = Booking.objects.filter(
                driver=driver
            ).exclude(status='COMPLETED').select_related('truck', 'user', 'load_type').order_by('-assigned_at', '-booking_date')[:20]
        
        # Calculate statistics
        all_driver_bookings = Booking.objects.filter(driver=driver)
        today_jobs = all_driver_bookings.filter(booking_date=today).count()
        pending_jobs = all_driver_bookings.filter(driver_status='ASSIGNED').count()
        completed_jobs = all_driver_bookings.filter(status='COMPLETED').count()
        
        # Weekly earnings (completed jobs)
        weekly_earnings = all_driver_bookings.filter(
            status='COMPLETED',
            booking_date__gte=week_ago
        ).aggregate(Sum('price'))['price__sum'] or 0
        
        # Get driver's truck location for navigation
        driver_truck = None
        truck_location = None
        if driver.assigned_truck:
            driver_truck = driver.assigned_truck
            if driver_truck.current_latitude and driver_truck.current_longitude:
                truck_location = {
                    'lat': driver_truck.current_latitude,
                    'lng': driver_truck.current_longitude
                }
    else:
        driver_bookings = []
        today_jobs = 0
        pending_jobs = 0
        completed_jobs = 0
        weekly_earnings = 0
        truck_location = None
    
    context = {
        'driver': request.user,
        'driver_profile': driver,
        'driver_bookings': driver_bookings,
        'today_jobs': today_jobs,
        'pending_jobs': pending_jobs,
        'completed_jobs': completed_jobs,
        'weekly_earnings': int(weekly_earnings),
        'truck_location': truck_location,
    }
    return render(request, "bookings/dashboard.html", context)


@login_required(login_url='/login/')
def driver_profile(request):
    """
    Driver profile view.
    
    URL: /driver-profile/
    Template: bookings/driver_profile.html
    """
    if request.user.role != 'DRIVER':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    try:
        driver = Driver.objects.get(user=request.user)
    except Driver.DoesNotExist:
        driver = None
    
    context = {
        'driver_profile': driver,
    }
    return render(request, "bookings/driver_profile.html", context)


@login_required(login_url='/login/')
def driver_jobs(request):
    """
    Driver jobs view - shows all assigned jobs with navigation.
    
    URL: /driver-jobs/
    Template: bookings/driver_jobs.html
    
    Features:
        - List of assigned jobs
        - GPS coordinates for pickup and drop locations
        - Navigation buttons using Google Maps
        - Browser Geolocation API for current location
        - Filter by status (all, today, active, completed)
    """
    if request.user.role != 'DRIVER':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    # Get driver profile
    try:
        driver = Driver.objects.get(user=request.user)
    except Driver.DoesNotExist:
        driver = None
        messages.error(request, "Driver profile not found.")
        return redirect('driver_dashboard')
    
    # Get view type from query params
    view_type = request.GET.get('view', 'all')
    today = timezone.now().date()
    
    # Get base queryset
    bookings_query = Booking.objects.filter(driver=driver)
    
    # Apply filters based on view type
    if view_type == 'today':
        driver_bookings = bookings_query.filter(booking_date=today)
    elif view_type == 'active':
        driver_bookings = bookings_query.exclude(status='COMPLETED')
    elif view_type == 'completed':
        driver_bookings = bookings_query.filter(status='COMPLETED')
    else:
        # All jobs - show pending/active first
        driver_bookings = bookings_query
    
    # Select related for efficiency and order
    driver_bookings = driver_bookings.select_related('truck', 'user', 'load_type', 'driver').order_by('-booking_date', '-created_at')
    
    # Get driver's truck location for fallback navigation
    truck_location = None
    if driver.assigned_truck:
        if driver.assigned_truck.current_latitude and driver.assigned_truck.current_longitude:
            truck_location = {
                'lat': driver.assigned_truck.current_latitude,
                'lng': driver.assigned_truck.current_longitude
            }
    
    context = {
        'driver': request.user,
        'driver_profile': driver,
        'driver_bookings': driver_bookings,
        'truck_location': truck_location,
        'view_type': view_type,
    }
    return render(request, "bookings/driver_jobs.html", context)


@login_required(login_url='/login/')
def driver_update_job_status(request, booking_id, new_status):
    """
    Update job status (driver action).
    
    URL: /driver/job/<booking_id>/<new_status>/
    
    Valid statuses:
        - PENDING
        - IN_PROGRESS
        - COMPLETED
    
    When status is COMPLETED, the truck is released.
    """
    if request.user.role != 'DRIVER':
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('login')
    
    try:
        driver = Driver.objects.get(user=request.user)
    except Driver.DoesNotExist:
        messages.error(request, "Driver profile not found.")
        return redirect('driver_dashboard')
    
    # Get company's trucks
    company_trucks = Truck.objects.filter(company=driver.company)
    
    try:
        booking = Booking.objects.get(id=booking_id, truck__in=company_trucks)
    except Booking.DoesNotExist:
        messages.error(request, "Booking not found.")
        return redirect('driver_dashboard')
    
    # Validate status
    valid_statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED']
    if new_status not in valid_statuses:
        messages.error(request, "Invalid status.")
        return redirect('driver_dashboard')
    
    # Update status
    booking.status = new_status
    booking.save()
    
    # If completed, release the truck
    if new_status == 'COMPLETED' and booking.truck:
        booking.truck.is_available = True
        booking.truck.save()
    
    messages.success(request, f"Job #{booking.id} status updated to {new_status.replace('_', ' ')}.")
    return redirect('driver_dashboard')


@login_required
def driver_accept_job(request, booking_id):
    """
    Driver accepts an assigned job.
    
    URL: /driver/job/<booking_id>/accept/
    """
    if request.user.role != 'DRIVER':
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('login')
    
    try:
        driver = Driver.objects.get(user=request.user)
    except Driver.DoesNotExist:
        messages.error(request, "Driver profile not found.")
        return redirect('driver_dashboard')
    
    company_trucks = Truck.objects.filter(company=driver.company)
    
    try:
        booking = Booking.objects.get(id=booking_id, truck__in=company_trucks, driver=driver)
    except Booking.DoesNotExist:
        messages.error(request, "Booking not found or not assigned to you.")
        return redirect('driver_dashboard')
    
    if booking.driver_status != 'ASSIGNED':
        messages.error(request, "This job is not available for acceptance.")
        return redirect('driver_dashboard')
    
    booking.driver_status = 'ACCEPTED'
    booking.status = 'IN_PROGRESS'
    booking.save()
    
    messages.success(request, f"Job #{booking.id} accepted! You can now start the trip.")
    return redirect('driver_dashboard')


@login_required
def driver_reject_job(request, booking_id):
    """
    Driver rejects an assigned job.
    
    URL: /driver/job/<booking_id>/reject/
    """
    if request.user.role != 'DRIVER':
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('login')
    
    try:
        driver = Driver.objects.get(user=request.user)
    except Driver.DoesNotExist:
        messages.error(request, "Driver profile not found.")
        return redirect('driver_dashboard')
    
    company_trucks = Truck.objects.filter(company=driver.company)
    
    try:
        booking = Booking.objects.get(id=booking_id, truck__in=company_trucks, driver=driver)
    except Booking.DoesNotExist:
        messages.error(request, "Booking not found or not assigned to you.")
        return redirect('driver_dashboard')
    
    if booking.driver_status != 'ASSIGNED':
        messages.error(request, "This job cannot be rejected.")
        return redirect('driver_dashboard')
    
    # Prevent rejection if job was assigned by company
    if booking.assigned_by_company:
        messages.error(request, "You cannot reject a job that was assigned by the company. Please contact your manager.")
        return redirect('driver_dashboard')
    
    booking.driver_status = 'REJECTED'
    booking.driver = None
    booking.save()
    
    messages.success(request, f"Job #{booking.id} has been rejected.")
    return redirect('driver_dashboard')


# =============================================================================
# SECTION 4: ADMIN DASHBOARD & MANAGEMENT VIEWS
# =============================================================================
# Views for admin users

@login_required(login_url='/login/')
def dashboard(request):
    """
    Default/legacy dashboard view.
    
    URL: /dashboard/
    """
    context = {
        "total_bookings": Booking.objects.count(),
        "total_revenue": Booking.objects.aggregate(Sum("price"))["price__sum"] or 0,
        "recent_bookings": Booking.objects.order_by("-booking_date")[:5],
    }
    return render(request, "bookings/dashboard.html", context)


@login_required(login_url='/login/')
def admin_dashboard(request):
    """
    Admin dashboard - system overview and statistics.
    
    URL: /admin-dashboard/
    Template: bookings/admin_dashboard.html
    
    Displays:
        - Total bookings
        - Total revenue
        - Recent bookings
        - Pending company approvals
    
    Access: Admin users only (is_staff, is_superuser, or role='ADMIN')
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Driver
    from pricing.models import Subscription
    
    context = {
        'total_bookings': Booking.objects.count(),
        'total_revenue': Booking.objects.aggregate(Sum("price"))["price__sum"] or 0,
        'total_users': User.objects.count(),
        'recent_bookings': Booking.objects.order_by("-booking_date")[:10],
        'pending_companies': Company.objects.filter(is_approved=False).count(),
        'total_trucks': Truck.objects.count(),
        'available_trucks': Truck.objects.filter(is_available=True).count(),
        'total_drivers': Driver.objects.count(),
        'active_subscriptions': Subscription.objects.filter(is_active=True).count(),
    }
    return render(request, "bookings/admin_dashboard.html", context)


# =============================================================================
# SECTION 5: ADMIN USER MANAGEMENT VIEWS
# =============================================================================

@login_required(login_url='/login/')
def admin_users(request):
    """
    Admin: View all users in the system.
    
    URL: /admin/users/
    Template: bookings/admin_users.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    users = User.objects.all().order_by('-date_joined')
    return render(request, "bookings/admin_users.html", {"users": users})


@login_required(login_url='/login/')
def admin_user_detail(request, user_id):
    """
    Admin: View detailed information about a user.
    
    URL: /admin/users/<user_id>/
    Template: bookings/admin_user_detail.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    user = get_object_or_404(User, id=user_id)
    return render(request, "bookings/admin_user_detail.html", {"user_obj": user})


@login_required(login_url='/login/')
def admin_user_delete(request, user_id):
    """
    Admin: Delete a user account.
    
    URL: /admin/users/<user_id>/delete/
    Template: bookings/admin_user_delete.html
    
    POST required for deletion (confirmation).
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect('admin_users')
    
    return render(request, "bookings/admin_user_delete.html", {"user_obj": user})


@login_required(login_url='/login/')
def admin_user_toggle_status(request, user_id):
    """
    Admin: Activate or deactivate a user account.
    
    URL: /admin/users/<user_id>/toggle-status/
    
    Prevents admin from deactivating their own account.
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent self-deactivation
    if user.id == request.user.id:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('admin_users')
    
    user.is_active = not user.is_active
    user.save()
    
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User '{user.username}' {status} successfully.")
    return redirect('admin_users')


@login_required(login_url='/login/')
def admin_user_change_role(request, user_id):
    """
    Admin: Change a user's role.
    
    URL: /admin/users/<user_id>/change-role/
    
    Valid roles: ADMIN, COMPANY, CUSTOMER, DRIVER
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')
        
        # Validate role
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if new_role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect('admin_user_detail', user_id=user_id)
        
        old_role = user.get_role_display()
        user.role = new_role
        user.save()
        
        messages.success(request, f"User '{user.username}' role changed from {old_role} to {user.get_role_display()}.")
        return redirect('admin_user_detail', user_id=user_id)
    
    return redirect('admin_user_detail', user_id=user_id)


@login_required(login_url='/login/')
def admin_reset_password(request, user_id):
    """
    Admin: Reset a user's password.
    
    URL: /admin/users/<user_id>/reset-password/
    
    Allows admin to reset a user's password without knowing the current password.
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not new_password:
            messages.error(request, "Password is required.")
            return redirect('admin_user_detail', user_id=user_id)
        
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('admin_user_detail', user_id=user_id)
        
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('admin_user_detail', user_id=user_id)
        
        # Set the new password
        user.set_password(new_password)
        user.save()
        
        messages.success(request, f"Password for '{user.username}' has been reset successfully.")
        return redirect('admin_user_detail', user_id=user_id)
    
    return redirect('admin_user_detail', user_id=user_id)


# =============================================================================
# SECTION 6: ADMIN TRUCK MANAGEMENT VIEWS
# =============================================================================

@login_required(login_url='/login/')
def admin_trucks(request):
    """
    Admin: View all trucks in the system.
    
    URL: /admin/trucks/
    Template: bookings/admin_trucks.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    trucks = Truck.objects.all().order_by('-created_at')
    return render(request, "bookings/admin_trucks.html", {"trucks": trucks})


@login_required(login_url='/login/')
def admin_truck_add(request):
    """
    Admin: Add a new truck to the system.
    
    URL: /admin/trucks/add/
    Template: bookings/admin_truck_add.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    if request.method == 'POST':
        truck_number = request.POST.get('truck_number')
        truck_type = request.POST.get('truck_type')
        capacity = float(request.POST.get('capacity'))
        price_per_km = float(request.POST.get('price_per_km'))
        company_id = request.POST.get('company')
        is_available = 'is_available' in request.POST
        image = request.FILES.get('image')
        
        company = None
        if company_id:
            company = get_object_or_404(Company, id=company_id)
        
        Truck.objects.create(
            company=company,
            truck_number=truck_number,
            truck_type=truck_type,
            capacity=capacity,
            price_per_km=price_per_km,
            is_available=is_available,
            image=image
        )
        messages.success(request, "Truck added successfully.")
        return redirect('admin_trucks')
    
    companies = Company.objects.filter(is_approved=True)
    truck_types = Truck.TRUCK_TYPES
    return render(request, "bookings/admin_truck_add.html", {
        "companies": companies,
        "truck_types": truck_types
    })


@login_required(login_url='/login/')
def admin_truck_edit(request, truck_id):
    """
    Admin: Edit truck details.
    
    URL: /admin/trucks/<truck_id>/edit/
    Template: bookings/admin_truck_edit.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    truck = get_object_or_404(Truck, id=truck_id)
    
    if request.method == 'POST':
        truck.truck_number = request.POST.get('truck_number')
        truck.truck_type = request.POST.get('truck_type')
        truck.capacity = float(request.POST.get('capacity'))
        truck.price_per_km = float(request.POST.get('price_per_km'))
        truck.is_available = 'is_available' in request.POST
        truck.save()
        messages.success(request, "Truck updated successfully.")
        return redirect('admin_trucks')
    
    return render(request, "bookings/admin_truck_edit.html", {"truck": truck})


@login_required(login_url='/login/')
def admin_truck_delete(request, truck_id):
    """
    Admin: Delete a truck.
    
    URL: /admin/trucks/<truck_id>/delete/
    Template: bookings/admin_truck_delete.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    truck = get_object_or_404(Truck, id=truck_id)
    
    if request.method == 'POST':
        truck.delete()
        messages.success(request, "Truck deleted successfully.")
        return redirect('admin_trucks')
    
    return render(request, "bookings/admin_truck_delete.html", {"truck": truck})


# =============================================================================
# SECTION 7: ADMIN COMPANY MANAGEMENT VIEWS
# =============================================================================

@login_required(login_url='/login/')
def admin_companies(request):
    """
    Admin: View all companies.
    
    URL: /admin/companies/
    Template: bookings/admin_companies.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    companies = Company.objects.all().order_by('-created_at')
    return render(request, "bookings/admin_companies.html", {"companies": companies})


@login_required(login_url='/login/')
def admin_company_approve(request, company_id):
    """
    Admin: Approve a company registration.
    
    URL: /admin/companies/<company_id>/approve/
    
    Sends approval notification email to company.
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    company = get_object_or_404(Company, id=company_id)
    company.is_approved = True
    company.save()
    
    # Send approval email
    try:
        from django.core.mail import send_mail
        send_mail(
            "Transova - Company Registration Approved",
            f"Dear {company.company_name},\n\n"
            f"Your company registration has been approved!\n\n"
            f"You can now log in to your dashboard and start managing your trucks and bookings.\n\n"
            f"Login URL: {request.build_absolute_uri('/login/')}\n\n"
            f"Best regards,\nTransova Team",
            "noreply@transova.com",
            [company.user.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
    
    messages.success(request, f"Company '{company.company_name}' approved successfully.")
    return redirect('admin_companies')


@login_required(login_url='/login/')
def admin_company_disapprove(request, company_id):
    """
    Admin: Disapprove a company registration.
    
    URL: /admin/companies/<company_id>/disapprove/
    
    Sends rejection notification email to company.
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    company = get_object_or_404(Company, id=company_id)
    company.is_approved = False
    company.save()
    
    # Send rejection email
    try:
        from django.core.mail import send_mail
        send_mail(
            "Transova - Company Registration Update",
            f"Dear {company.company_name},\n\n"
            f"We regret to inform you that your company registration has been disapproved.\n\n"
            f"If you believe this is an error or would like to resubmit your application, please contact our support team.\n\n"
            f"Best regards,\nTransova Team",
            "noreply@transova.com",
            [company.user.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
    
    messages.success(request, f"Company '{company.company_name}' disapproved.")
    return redirect('admin_companies')


@login_required(login_url='/login/')
def admin_drivers(request):
    """
    Admin: View all drivers.
    
    URL: /admin/drivers/
    Template: bookings/admin_drivers.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    drivers = Driver.objects.all().select_related('user', 'company')
    return render(request, "bookings/admin_drivers.html", {"drivers": drivers})


# =============================================================================
# SECTION 8: ADMIN LOAD TYPE MANAGEMENT VIEWS
# =============================================================================

@login_required(login_url='/login/')
def admin_load_types(request):
    """
    Admin: View all load types.
    
    URL: /admin/load-types/
    Template: bookings/admin_load_types.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    load_types = LoadType.objects.all()
    return render(request, "bookings/admin_load_types.html", {"load_types": load_types})


@login_required(login_url='/login/')
def admin_load_type_add(request):
    """
    Admin: Add a new load type.
    
    URL: /admin/load-types/add/
    Template: bookings/admin_load_type_form.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    if request.method == 'POST':
        LoadType.objects.create(
            name=request.POST.get('name'),
            price_multiplier=float(request.POST.get('price_multiplier'))
        )
        messages.success(request, "Load type added successfully.")
        return redirect('admin_load_types')
    
    return render(request, "bookings/admin_load_type_form.html", {"load_type": None})


@login_required(login_url='/login/')
def admin_load_type_edit(request, load_type_id):
    """
    Admin: Edit a load type.
    
    URL: /admin/load-types/<load_type_id>/edit/
    Template: bookings/admin_load_type_form.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    load_type = get_object_or_404(LoadType, id=load_type_id)
    
    if request.method == 'POST':
        load_type.name = request.POST.get('name')
        load_type.price_multiplier = float(request.POST.get('price_multiplier'))
        load_type.save()
        messages.success(request, "Load type updated successfully.")
        return redirect('admin_load_types')
    
    return render(request, "bookings/admin_load_type_form.html", {"load_type": load_type})


@login_required(login_url='/login/')
def admin_load_type_delete(request, load_type_id):
    """
    Admin: Delete a load type.
    
    URL: /admin/load-types/<load_type_id>/delete/
    Template: bookings/admin_load_type_delete.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    load_type = get_object_or_404(LoadType, id=load_type_id)
    
    if request.method == 'POST':
        load_type.delete()
        messages.success(request, "Load type deleted successfully.")
        return redirect('admin_load_types')
    
    return render(request, "bookings/admin_load_type_delete.html", {"load_type": load_type})


# =============================================================================
# SECTION 9: ADMIN SUBSCRIPTION MANAGEMENT VIEWS
# =============================================================================

@login_required(login_url='/login/')
def admin_subscriptions(request):
    """
    Admin: View all subscriptions.
    
    URL: /admin/subscriptions/
    Template: bookings/admin_subscriptions.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from pricing.models import Subscription
    subscriptions = Subscription.objects.all().order_by('-start_date')
    return render(request, "bookings/admin_subscriptions.html", {"subscriptions": subscriptions})


@login_required(login_url='/login/')
def admin_subscription_toggle(request, subscription_id):
    """
    Admin: Toggle subscription active status.
    
    URL: /admin/subscriptions/<subscription_id>/toggle/
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from pricing.models import Subscription
    subscription = get_object_or_404(Subscription, id=subscription_id)
    subscription.is_active = not subscription.is_active
    subscription.save()
    status = "activated" if subscription.is_active else "deactivated"
    messages.success(request, f"Subscription {status} successfully.")
    return redirect('admin_subscriptions')


# =============================================================================
# SECTION 10: ADMIN API ENDPOINTS
# =============================================================================

@login_required(login_url='/login/')
def admin_stats(request):
    """
    Admin: Get system statistics as JSON.
    
    URL: /admin/stats/
    
    Returns:
        JSON with various system statistics
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    
    from fleet.models import Driver
    from pricing.models import LoadType, Subscription
    
    return JsonResponse({
        "total_bookings": Booking.objects.count(),
        "total_revenue": float(Booking.objects.aggregate(Sum("price"))["price__sum"] or 0),
        "total_users": User.objects.count(),
        "total_trucks": Truck.objects.count(),
        "available_trucks": Truck.objects.filter(is_available=True).count(),
        "total_companies": Company.objects.count(),
        "approved_companies": Company.objects.filter(is_approved=True).count(),
        "pending_companies": Company.objects.filter(is_approved=False).count(),
        "total_drivers": Driver.objects.count(),
        "total_load_types": LoadType.objects.count(),
        "active_subscriptions": Subscription.objects.filter(is_active=True).count(),
    })


@login_required(login_url='/login/')
def company_status_check(request):
    """
    API endpoint for company to check approval status.
    
    URL: /api/company/status/
    
    Returns:
        JSON with company's approval status
    """
    if request.user.role != 'COMPANY':
        return JsonResponse({"error": "Unauthorized"}, status=401)
    
    try:
        company = Company.objects.get(user=request.user)
        return JsonResponse({
            "is_approved": company.is_approved,
            "company_name": company.company_name,
        })
    except Company.DoesNotExist:
        return JsonResponse({"error": "Company profile not found"}, status=404)


# =============================================================================
# SECTION 11: PAYMENT VIEWS
# =============================================================================

def payment(request):
    """
    Payment page view.
    
    URL: /payment/
    Template: bookings/payment.html
    
    Query Parameters:
        - amount: Payment amount
        - currency: Currency code
        - booking_id: Associated booking ID
    """
    amount = request.GET.get('amount', 0)
    currency = request.GET.get('currency', 'USD')
    booking_id = request.GET.get('booking_id', None)
    
    booking = None
    if booking_id:
        booking = Booking.objects.filter(id=booking_id).first()
    
    context = {
        'amount': amount,
        'currency': currency,
        'booking_id': booking_id,
        'booking': booking,
    }
    return render(request, "bookings/payment.html", context)


@csrf_exempt
def process_payment(request):
    """
    Process payment and create payment record.
    
    URL: /process-payment/
    Method: POST
    
    Request Body:
        - booking_id: ID of the booking to pay for
        - payment_method: CARD, WALLET, etc.
        - card_number: Card number (for CARD method)
        - card_expiry: Expiry date
        - card_cvv: CVV
        - cardholder_name: Name on card
    
    Returns:
        JSON with success status and transaction ID
    
    Note:
        This is a demo implementation. In production, integrate
        with a real payment gateway (Stripe, PayPal, etc.)
    """
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except:
            data = request.POST
        
        booking_id = data.get('booking_id')
        payment_method = data.get('payment_method', 'CARD')
        card_number = data.get('card_number', '')
        card_expiry = data.get('card_expiry', '')
        card_cvv = data.get('card_cvv', '')
        cardholder_name = data.get('cardholder_name', '')
        
        # Validate required fields
        if not booking_id:
            return JsonResponse({'success': False, 'error': 'Booking ID is required'}, status=400)
        
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Booking not found'}, status=404)
        
        # Validate card details for CARD payments
        if payment_method == 'CARD':
            if not card_number or len(card_number.replace(' ', '')) < 13:
                return JsonResponse({'success': False, 'error': 'Invalid card number'}, status=400)
            if not card_expiry or len(card_expiry) < 4:
                return JsonResponse({'success': False, 'error': 'Invalid expiry date'}, status=400)
            if not card_cvv or len(card_cvv) < 3:
                return JsonResponse({'success': False, 'error': 'Invalid CVV'}, status=400)
        
        # Detect card type using utility function
        card_type = detect_card_type(card_number)
        
        # Get last 4 digits for records
        card_last_four = mask_card_number(card_number).replace('*', '')
        
        # Generate unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Create payment record
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.price,
            currency=booking.currency,
            payment_method=payment_method,
            status='SUCCESS',
            transaction_id=transaction_id,
            card_last_four=card_last_four,
            card_type=card_type
        )
        
        # Update booking payment status
        booking.payment_status = 'PAID'
        booking.save()
        
        return JsonResponse({
            'success': True,
            'transaction_id': transaction_id,
            'message': 'Payment processed successfully'
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


def payment_success(request):
    """
    Payment success page.
    
    URL: /payment/success/
    Template: bookings/payment_success.html
    
    Redirects user to appropriate dashboard based on role.
    """
    booking_id = request.GET.get('booking_id')
    transaction_id = request.GET.get('transaction_id', '')
    
    if booking_id:
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.payment_status = 'PAID'
            booking.save()
        except Booking.DoesNotExist:
            pass
    
    # Determine redirect based on user role
    redirect_url = '/'
    if request.user.is_authenticated:
        if request.user.role == 'CUSTOMER':
            redirect_url = '/bookings/customer-dashboard/'
        elif request.user.role == 'DRIVER':
            redirect_url = '/bookings/driver-dashboard/'
        elif request.user.role == 'COMPANY':
            redirect_url = '/fleet/dashboard/'
        elif request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN':
            redirect_url = '/bookings/admin-dashboard/'
    
    return render(request, "bookings/payment_success.html", {
        'redirect_url': redirect_url,
        'booking_id': booking_id,
        'transaction_id': transaction_id
    })


def payment_cancel(request):
    """
    Payment cancellation page.
    
    URL: /payment/cancel/
    Template: bookings/payment_cancel.html
    
    When payment is cancelled:
        - Associated truck is released
        - Booking is deleted
    """
    booking_id = request.GET.get('booking_id')
    if booking_id:
        try:
            booking = Booking.objects.get(id=booking_id)
            # Release the truck
            if booking.truck:
                booking.truck.is_available = True
                booking.truck.save()
            booking.delete()
        except Booking.DoesNotExist:
            pass
    
    return render(request, "bookings/payment_cancel.html")


# =============================================================================
# SECTION 12: UTILITY VIEWS
# =============================================================================

def faq(request):
    """
    Frequently Asked Questions page.
    
    URL: /faq/
    Template: bookings/faq.html
    
    Displays:
        - Static FAQ questions and answers
        - Form to submit new questions
        - List of publicly answered questions
    """
    # Get public answered FAQs
    public_faqs = FAQQuestion.objects.filter(
        status='ANSWERED',
        is_public=True
    ).order_by('-answered_at')
    
    # Get user's submitted questions (if logged in)
    user_questions = []
    if request.user.is_authenticated:
        user_questions = FAQQuestion.objects.filter(
            user=request.user
    ).order_by('-created_at')
    
    context = {
        'public_faqs': public_faqs,
        'user_questions': user_questions,
    }
    return render(request, "bookings/faq.html", context)


@csrf_exempt
def faq_submit(request):
    """
    Submit a new FAQ question.
    
    URL: /faq/submit/
    Method: POST
    
    Request Body:
        - subject: Question subject
        - question: Question details
        - email: Contact email (for guests)
    """
    if request.method == 'POST':
        subject = request.POST.get('subject')
        question_text = request.POST.get('question')
        email = request.POST.get('email', '')
        
        if not subject or not question_text:
            messages.error(request, "Subject and question are required.")
            return redirect('faq')
        
        # If user is logged in, associate with user
        user = None
        if request.user.is_authenticated:
            user = request.user
            email = user.email
        elif not email:
            messages.error(request, "Email is required for guest submissions.")
            return redirect('faq')
        
        # Create the question
        faq_question = FAQQuestion.objects.create(
            user=user,
            email=email,
            subject=subject,
            question=question_text,
            status='PENDING'
        )
        
        messages.success(request, "Your question has been submitted! We'll get back to you soon.")
        return redirect('faq')
    
    return redirect('faq')


@login_required(login_url='/login/')
def faq_reply(request, question_id):
    """
    Admin view to reply to a FAQ question.
    
    URL: /faq/<question_id>/reply/
    Method: POST
    
    Access: Admin users only
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    faq_question = get_object_or_404(FAQQuestion, id=question_id)
    
    if request.method == 'POST':
        answer = request.POST.get('answer')
        is_public = 'is_public' in request.POST
        
        if not answer:
            messages.error(request, "Answer is required.")
            return redirect('admin_faq')
        
        faq_question.answer = answer
        faq_question.replied_by = request.user
        faq_question.status = 'ANSWERED'
        faq_question.is_public = is_public
        faq_question.answered_at = timezone.now()
        faq_question.save()
        
        # Send email notification to user
        try:
            from django.core.mail import send_mail
            send_mail(
                f"Transova FAQ - Your question has been answered",
                f"Dear User,\n\n"
                f"Your question has been answered!\n\n"
                f"Question: {faq_question.subject}\n"
                f"Answer: {answer}\n\n"
                f"You can view this and more FAQs on our website.\n\n"
                f"Best regards,\nTransova Team",
                "noreply@transova.com",
                [faq_question.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"FAQ reply email failed: {e}")
        
        messages.success(request, "Reply sent successfully!")
        return redirect('admin_faq')
    
    return redirect('admin_faq')


@login_required(login_url='/login/')
def admin_faq(request):
    """
    Admin view to manage FAQ questions.
    
    URL: /admin/faq/
    Template: bookings/admin_faq.html
    
    Access: Admin users only
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    questions = FAQQuestion.objects.all().order_by('-created_at')
    
    if status_filter == 'pending':
        questions = questions.filter(status='PENDING')
    elif status_filter == 'answered':
        questions = questions.filter(status='ANSWERED')
    
    context = {
        'questions': questions,
        'status_filter': status_filter,
    }
    return render(request, "bookings/admin_faq.html", context)


@login_required(login_url='/login/')
def admin_faq_toggle_public(request, question_id):
    """
    Admin view to toggle FAQ question public/private status.
    
    URL: /admin/faq/<question_id>/toggle-public/
    Method: POST
    
    Access: Admin users only
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    faq_question = get_object_or_404(FAQQuestion, id=question_id)
    
    # Toggle public status
    faq_question.is_public = not faq_question.is_public
    faq_question.save()
    
    status = "public" if faq_question.is_public else "private"
    messages.success(request, f"FAQ question is now {status}.")
    return redirect('admin_faq')


# =============================================================================
# SECTION 13: AUTHENTICATION FORMS & VIEWS
# =============================================================================

class EmailAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form using email instead of username.
    
    This form extends Django's AuthenticationForm to allow
    users to log in with their email address instead of username.
    
    Fields:
        - username: Email field
        - password: Password field
    """
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control minimal-select', 
            'placeholder': 'Email'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control minimal-select', 
            'placeholder': 'Password'
        })
    )


class RoleBasedLoginView(LoginView):
    """
    Login view with role-based redirect.
    
    After successful login, redirects users based on their role:
        - ADMIN/is_staff: /bookings/admin-dashboard/
        - COMPANY (approved): /fleet/dashboard/
        - COMPANY (pending): /fleet/pending/
        - CUSTOMER: /
        - DRIVER: /bookings/driver-dashboard/
    
    Template: accounts/login.html
    """
    template_name = "accounts/login.html"
    form_class = EmailAuthenticationForm

    def get_success_url(self):
        user = self.request.user
        
        # Admin redirect
        if user.is_staff or user.is_superuser or user.role == 'ADMIN':
            return "/bookings/admin-dashboard/"
        
        # Company redirect - check if approved
        if user.role == 'COMPANY':
            try:
                company = user.company_profile
                if company.is_approved:
                    return "/fleet/dashboard/"
                else:
                    return "/fleet/pending/"
            except Company.DoesNotExist:
                return "/company-register/"
        
        # Customer redirect
        if user.role == 'CUSTOMER':
            return "/bookings/customer-dashboard/"
        
        # Driver redirect
        if user.role == 'DRIVER':
            return "/bookings/driver-dashboard/"
        
        # Default fallback
        return "/"


def logout_view(request):
    """
    Logout view - ends user session and redirects to login.
    
    URL: /logout/
    """
    logout(request)
    return redirect("login")


# =============================================================================
# SECTION 14: PASSWORD MANAGEMENT VIEWS
# =============================================================================

def resend_otp(request):
    """
    Resend OTP for email verification.
    
    URL: /resend-otp/
    """
    otp = generate_otp()
    request.session["otp"] = otp

    send_mail(
        "Transova OTP Verification",
        f"Your new OTP is {otp}",
        "noreply@transova.com",
        [request.session["reg_data"]["email"]],
    )
    return redirect("verify_otp")


def forgot_password(request):
    """
    Forgot password - sends OTP to user's email.
    
    URL: /forgot-password/
    Template: accounts/forgot_password.html
    
    Flow:
        1. User enters email
        2. OTP is sent to email
        3. User enters OTP and new password
    """
    if request.method == "POST":
        email = request.POST.get("email")

        if not User.objects.filter(email=email).exists():
            messages.error(request, "Email not registered")
            return redirect("forgot_password")

        otp = generate_otp()
        request.session["reset_otp"] = otp
        request.session["reset_email"] = email

        send_mail(
            "Transova Password Reset",
            f"Your OTP is {otp}",
            "noreply@transova.com",
            [email],
        )
        return redirect("reset_password")

    return render(request, "accounts/forgot_password.html")


def reset_password(request):
    """
    Reset password using OTP verification.
    
    URL: /reset-password/
    Template: accounts/reset_password.html
    
    Requires valid OTP stored in session.
    """
    if request.method == "POST":
        if int(request.POST.get("otp")) == request.session.get("reset_otp"):
            user = User.objects.get(email=request.session["reset_email"])
            user.set_password(request.POST.get("password"))
            user.save()
            
            # Clear session
            request.session.pop('reset_otp', None)
            request.session.pop('reset_email', None)
            
            messages.success(request, "Password reset successfully! Please log in.")
            return redirect("login")
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("reset_password")

    return render(request, "accounts/reset_password.html")


# =============================================================================
# SECTION 15: REGISTRATION VIEWS
# =============================================================================

def register(request):
    """
    User registration with OTP verification.
    
    URL: /register/
    Template: accounts/register.html
    
    Registration Flow:
        1. User fills registration form
        2. System validates email (must be Gmail)
        3. OTP is sent to email
        4. User verifies OTP
        5. Account is created
    
    Restrictions:
        - Only Gmail addresses allowed
        - Email and username must be unique
    """
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Gmail-only check
        if not email.endswith("@gmail.com"):
            messages.error(request, "Only Gmail IDs are allowed")
            return redirect("register")

        # Check for duplicates
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already used")
            return redirect("register")

        # Generate OTP and store in session
        otp = generate_otp()
        request.session["otp"] = otp
        request.session["reg_data"] = {
            "username": username,
            "email": email,
            "password": password
        }

        # Send OTP via email
        send_mail(
            "Transova Email Verification",
            f"Your OTP is {otp}",
            "noreply@transova.com",
            [email],
        )

        return redirect("verify_otp")

    return render(request, "accounts/register.html")


def verify_otp(request):
    """
    OTP verification for registration.
    
    URL: /verify-otp/
    Template: accounts/verify_otp.html
    
    Validates OTP entered by user against session-stored OTP.
    """
    reg_data = request.session.get("reg_data")
    if not reg_data:
        messages.error(request, "Session expired. Please register again.")
        return redirect("register")

    email = reg_data.get("email")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("otp")

        if str(entered_otp) == str(session_otp):
            # OTP is correct, create user
            User.objects.create_user(
                username=reg_data["username"],
                email=reg_data["email"],
                password=reg_data["password"]
            )
            
            # Clear session
            del request.session["otp"]
            del request.session["reg_data"]

            messages.success(request, "Registration successful! You can now log in.")
            return redirect("login")
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("verify_otp")

    return render(request, "accounts/verify_otp.html", {"email": email})


# =============================================================================
# SECTION 16: COMPANY REGISTRATION & MANAGEMENT
# =============================================================================

def company_register(request):
    """
    Company registration with admin approval required.
    
    URL: /company-register/
    Template: accounts/company_register.html
    
    Registration Flow:
        1. Company fills registration form
        2. User account created with COMPANY role
        3. Company profile created (is_approved=False)
        4. Admin is notified
        5. Admin approves/rejects company
    
    Note:
        Company cannot log in until approved by admin.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        company_name = request.POST.get('company_name')
        trade_license = request.POST.get('trade_license')
        phone = request.POST.get('phone')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("company_register")
        
        # Create user with COMPANY role
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            role='COMPANY'
        )

        # Create company profile
        company = Company.objects.create(
            user=user,
            company_name=company_name,
            trade_license=trade_license,
            phone=phone,
            is_approved=False  # Requires admin approval
        )

        # Send notification to admin
        from django.conf import settings
        admin_email = getattr(settings, 'EMAIL_HOST_USER', 'admin@transova.com')
        
        try:
            send_mail(
                f"New Company Registration: {company_name}",
                f"A new company has registered on Transova and is waiting for approval.\n\n"
                f"Company Name: {company_name}\n"
                f"Email: {email}\n"
                f"Phone: {phone}\n"
                f"Trade License: {trade_license}\n\n"
                f"Please login to admin panel to approve or reject this company.",
                "noreply@transova.com",
                [admin_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Admin notification email failed: {e}")

        messages.success(request, "Company registration submitted! Please wait for admin approval.")
        return redirect('company_pending')

    return render(request, 'accounts/company_register.html')


def company_pending(request):
    """
    Company pending approval page.
    
    URL: /company-pending/ (or /fleet/pending/)
    Template: accounts/company_pending.html or fleet/company_pending.html
    
    Shown to companies that haven't been approved yet.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')
    
    if company.is_approved:
        return redirect('company_dashboard')
    
    return render(request, 'accounts/company_pending.html', {'company': company})


# =============================================================================
# SECTION 17: BIDDING SYSTEM VIEWS
# =============================================================================

@login_required(login_url='/login/')
def available_jobs(request):
    """
    View available jobs for companies to bid on.
    
    URL: /jobs/available/
    Template: bookings/available_jobs.html
    
    Shows pending bookings that don't have bids yet.
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "Only companies can view available jobs.")
        return redirect('login')
    
    try:
        company = Company.objects.get(user=request.user)
        if not company.is_approved:
            return redirect('company_pending')
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')
    
    # Get available jobs (pending bookings without accepted bids)
    available_bookings = Booking.objects.filter(
        status='PENDING'
    ).exclude(
        bids__company=company
    ).order_by('-booking_date')
    
    context = {
        'bookings': available_bookings,
        'company': company,
    }
    return render(request, 'bookings/available_jobs.html', context)


@login_required(login_url='/login/')
def submit_bid(request, booking_id):
    """
    Submit a bid for a job.
    
    URL: /jobs/<booking_id>/bid/
    Template: bookings/submit_bid.html
    """
    if request.user.role != 'COMPANY':
        return JsonResponse({'error': 'Only companies can submit bids'}, status=403)
    
    try:
        company = Company.objects.get(user=request.user)
        if not company.is_approved:
            return JsonResponse({'error': 'Company not approved'}, status=403)
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    booking = get_object_or_404(Booking, id=booking_id, status='PENDING')
    
    # Check if already bid
    if Bid.objects.filter(booking=booking, company=company).exists():
        messages.error(request, "You have already submitted a bid for this job.")
        return redirect('available_jobs')
    
    if request.method == 'POST':
        bid_amount = float(request.POST.get('bid_amount'))
        notes = request.POST.get('notes', '')
        truck_id = request.POST.get('truck')
        driver_id = request.POST.get('driver')
        
        truck = get_object_or_404(Truck, id=truck_id, company=company)
        driver = None
        if driver_id:
            driver = Driver.objects.filter(id=driver_id, company=company).first()
        
        Bid.objects.create(
            booking=booking,
            company=company,
            truck=truck,
            driver=driver,
            bid_amount=bid_amount,
            notes=notes
        )
        
        messages.success(request, "Bid submitted successfully!")
        return redirect('available_jobs')
    
    trucks = Truck.objects.filter(company=company, is_available=True)
    drivers = Driver.objects.filter(company=company, is_available=True)
    
    context = {
        'booking': booking,
        'trucks': trucks,
        'drivers': drivers,
    }
    return render(request, 'bookings/submit_bid.html', context)


@login_required(login_url='/login/')
def my_bids(request):
    """
    View company's submitted bids.
    
    URL: /jobs/my-bids/
    Template: bookings/my_bids.html
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "Only companies can view bids.")
        return redirect('login')
    
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')
    
    bids = Bid.objects.filter(company=company).order_by('-created_at')
    
    context = {
        'bids': bids,
        'company': company,
    }
    return render(request, 'bookings/my_bids.html', context)


@login_required(login_url='/login/')
def customer_view_bids(request, booking_id):
    """
    View and accept bids for a customer's booking.
    
    URL: /bookings/<booking_id>/bids/
    Template: bookings/customer_bids.html
    """
    if request.user.role != 'CUSTOMER':
        messages.error(request, "Only customers can view bids.")
        return redirect('login')
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify ownership
    if booking.user != request.user:
        messages.error(request, "You can only view bids for your own bookings.")
        return redirect('customer_dashboard')
    
    bids = Bid.objects.filter(booking=booking, status='PENDING').order_by('bid_amount')
    
    context = {
        'booking': booking,
        'bids': bids,
    }
    return render(request, 'bookings/customer_bids.html', context)


@login_required(login_url='/login/')
def accept_bid(request, bid_id):
    """
    Accept a bid and assign the truck/driver.
    
    URL: /bids/<bid_id>/accept/
    """
    if request.user.role != 'CUSTOMER':
        return JsonResponse({'error': 'Only customers can accept bids'}, status=403)
    
    bid = get_object_or_404(Bid, id=bid_id, status='PENDING')
    booking = bid.booking
    
    # Verify ownership
    if booking.user != request.user:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    # Accept this bid
    bid.status = 'ACCEPTED'
    bid.save()
    
    # Update booking - Auto-accept for company-assigned jobs
    # Driver cannot reject company-assigned jobs
    booking.truck = bid.truck
    booking.driver = bid.driver
    booking.status = 'IN_PROGRESS'
    booking.driver_status = 'ACCEPTED'  # Auto-accept so driver cannot reject
    booking.assigned_by_company = True  # Mark as company assigned - driver cannot reject
    booking.assigned_at = timezone.now()  # Set assignment time
    booking.save()
    
    # Mark truck as unavailable
    bid.truck.is_available = False
    bid.truck.save()
    
    # Reject other bids
    Bid.objects.filter(booking=booking).exclude(id=bid_id).update(status='REJECTED')
    
    messages.success(request, f"Bid accepted! Truck {bid.truck.truck_number} has been assigned.")
    return redirect('customer_dashboard')


# =============================================================================
# SECTION 18: GPS TRACKING VIEWS
# =============================================================================

@login_required(login_url='/login/')
def live_tracking(request):
    """
    Live GPS tracking view for trucks.
    
    URL: /tracking/live/
    Template: bookings/live_tracking.html
    
    Shows real-time location of all trucks.
    """
    if request.user.role not in ['COMPANY', 'ADMIN']:
        if not request.user.is_staff:
            messages.error(request, "You are not authorized to view this page.")
            return redirect('login')
    
    trucks = Truck.objects.filter(
        current_latitude__isnull=False,
        current_longitude__isnull=False
    ).select_related('company')
    
    context = {
        'trucks': trucks,
    }
    return render(request, 'bookings/live_tracking.html', context)


@csrf_exempt
@login_required(login_url='/login/')
def update_truck_location(request):
    """
    API endpoint to update truck GPS location.
    
    URL: /api/truck/<truck_id>/location/
    Method: POST
    
    Request Body:
        - latitude: Truck latitude
        - longitude: Truck longitude
    """
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except:
            data = request.POST
        
        truck_id = data.get('truck_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not truck_id or latitude is None or longitude is None:
            return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)
        
        try:
            truck = Truck.objects.get(id=truck_id)
            
            # Verify company owns this truck
            if request.user.role == 'COMPANY':
                try:
                    company = Company.objects.get(user=request.user)
                    if truck.company != company:
                        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
                except Company.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Company not found'}, status=403)
            
            truck.current_latitude = latitude
            truck.current_longitude = longitude
            truck.last_location_update = timezone.now()
            truck.is_online = True
            truck.save()
            
            return JsonResponse({'success': True})
        except Truck.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Truck not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=405)


@login_required(login_url='/login/')
def get_truck_locations(request):
    """
    API endpoint to get all truck locations (JSON).
    
    URL: /api/trucks/locations/
    """
    trucks = Truck.objects.filter(
        current_latitude__isnull=False,
        current_longitude__isnull=False
    ).values('id', 'truck_number', 'current_latitude', 'current_longitude', 
             'last_location_update', 'is_online', 'company__company_name')
    
    return JsonResponse({'trucks': list(trucks)})


# =============================================================================
# SECTION 19: WALLET & ESCROW VIEWS
# =============================================================================

@login_required(login_url='/login/')
def company_wallet(request):
    """
    Company wallet dashboard.
    
    URL: /fleet/wallet/
    Template: fleet/company_wallet.html
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "Only companies can view wallet.")
        return redirect('login')
    
    try:
        company = Company.objects.get(user=request.user)
        if not company.is_approved:
            return redirect('company_pending')
        
        wallet, created = Wallet.objects.get_or_create(company=company)
        transactions = wallet.transactions.all()[:20]
        
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'company': company,
    }
    return render(request, 'fleet/company_wallet.html', context)


@login_required(login_url='/login/')
def request_payout(request):
    """
    Request a payout from wallet.
    
    URL: /fleet/wallet/payout/
    """
    if request.user.role != 'COMPANY':
        return JsonResponse({'error': 'Only companies can request payouts'}, status=403)
    
    try:
        company = Company.objects.get(user=request.user)
        wallet = Wallet.objects.get(company=company)
    except (Company.DoesNotExist, Wallet.DoesNotExist):
        return JsonResponse({'error': 'Wallet not found'}, status=404)
    
    if request.method == 'POST':
        amount = float(request.POST.get('amount'))
        
        if amount > wallet.available_balance:
            return JsonResponse({'success': False, 'error': 'Insufficient balance'}, status=400)
        
        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'Invalid amount'}, status=400)
        
        success = wallet.process_payout(amount, f"Payout requested for {company.company_name}")
        
        if success:
            return JsonResponse({'success': True, 'message': 'Payout request submitted successfully'})
        else:
            return JsonResponse({'success': False, 'error': 'Payout failed'}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=405)


@login_required(login_url='/login/')
def admin_wallets(request):
    """
    Admin view all company wallets.
    
    URL: /admin/wallets/
    Template: bookings/admin_wallets.html
    """
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    wallets = Wallet.objects.all().select_related('company')
    
    context = {
        'wallets': wallets,
    }
    return render(request, 'bookings/admin_wallets.html', context)


# =============================================================================
# SECTION 20: PROOF OF DELIVERY VIEWS
# =============================================================================

@login_required(login_url='/login/')
def driver_delivery_proof(request, booking_id):
    """
    Driver uploads proof of delivery.
    
    URL: /driver/job/<booking_id>/proof/
    Template: bookings/driver_delivery_proof.html
    """
    if request.user.role != 'DRIVER':
        messages.error(request, "Only drivers can upload proof of delivery.")
        return redirect('login')
    
    try:
        driver = Driver.objects.get(user=request.user)
    except Driver.DoesNotExist:
        messages.error(request, "Driver profile not found.")
        return redirect('driver_dashboard')
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify driver is assigned to this booking
    # Check both direct driver assignment and truck-based assignment (for company-assigned jobs)
    is_assigned = False
    if booking.driver == driver:
        is_assigned = True
    elif booking.truck and hasattr(booking.truck, 'assigned_drivers'):
        # Check if this driver is assigned to the truck
        if booking.truck.assigned_drivers.filter(id=driver.id).exists():
            is_assigned = True
    
    if not is_assigned:
        messages.error(request, "You are not assigned to this job.")
        return redirect('driver_dashboard')
    
    # Check if proof already exists
    proof, created = ProofOfDelivery.objects.get_or_create(booking=booking)
    
    if request.method == 'POST':
        proof.delivery_photo = request.FILES.get('delivery_photo')
        proof.signature_image = request.FILES.get('signature_image')
        proof.received_by = request.POST.get('received_by', '')
        proof.notes = request.POST.get('notes', '')
        proof.latitude = request.POST.get('latitude')
        proof.longitude = request.POST.get('longitude')
        proof.save()
        
        # Update booking status to completed
        booking.status = 'COMPLETED'
        booking.save()
        
        # Release the truck
        if booking.truck:
            booking.truck.is_available = True
            booking.truck.save()
        
        # Process payment - hold in escrow until delivery
        if booking.truck and booking.truck.company:
            try:
                wallet = Wallet.objects.get(company=booking.truck.company)
                # Hold in escrow
                wallet.hold_in_escrow(
                    amount=booking.price,
                    booking=booking,
                    description=f"Escrow hold for Booking #{booking.id}"
                )
            except Wallet.DoesNotExist:
                pass
        
        messages.success(request, "Proof of delivery submitted successfully!")
        return redirect('driver_dashboard')
    
    # Generate Google Maps navigation URL
    navigation_url = None
    if booking.drop_lat and booking.drop_lng:
        navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={booking.drop_lat},{booking.drop_lng}"
    
    context = {
        'booking': booking,
        'proof': proof,
        'navigation_url': navigation_url,
    }
    return render(request, 'bookings/driver_delivery_proof.html', context)


@login_required(login_url='/login/')
def view_proof_of_delivery(request, booking_id):
    """
    View proof of delivery for a booking.
    
    URL: /bookings/<booking_id>/proof/
    Template: bookings/view_proof.html
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify access
    if request.user.role == 'CUSTOMER':
        if booking.user != request.user:
            messages.error(request, "You are not authorized to view this.")
            return redirect('customer_dashboard')
    elif request.user.role == 'COMPANY':
        try:
            company = Company.objects.get(user=request.user)
            if booking.truck and booking.truck.company != company:
                messages.error(request, "You are not authorized to view this.")
                return redirect('company_dashboard')
        except Company.DoesNotExist:
            pass
    elif not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this.")
        return redirect('login')
    
    try:
        proof = ProofOfDelivery.objects.get(booking=booking)
    except ProofOfDelivery.DoesNotExist:
        messages.error(request, "Proof of delivery not found.")
        return redirect('booking_receipt', booking_id=booking_id)
    
    context = {
        'booking': booking,
        'proof': proof,
    }
    return render(request, 'bookings/view_proof.html', context)


# =============================================================================
# SECTION 21: PAYMENT WITH ESCROW
# =============================================================================

@csrf_exempt
def process_payment_with_escrow(request):
    """
    Process payment and hold in escrow.
    
    URL: /process-payment-escrow/
    Method: POST
    """
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except:
            data = request.POST
        
        booking_id = data.get('booking_id')
        payment_method = data.get('payment_method', 'CARD')
        
        if not booking_id:
            return JsonResponse({'success': False, 'error': 'Booking ID required'}, status=400)
        
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Booking not found'}, status=404)
        
        # Create payment
        transaction_id = str(uuid.uuid4())
        
        Payment.objects.create(
            booking=booking,
            amount=booking.price,
            currency=booking.currency,
            payment_method=payment_method,
            status='SUCCESS',
            transaction_id=transaction_id
        )
        
        # Update booking
        booking.payment_status = 'PAID'
        booking.save()
        
        # Hold in escrow if company assigned
        if booking.truck and booking.truck.company:
            try:
                wallet = Wallet.objects.get(company=booking.truck.company)
                wallet.hold_in_escrow(
                    amount=booking.price,
                    booking=booking,
                    description=f"Payment received for Booking #{booking.id}"
                )
            except Wallet.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'transaction_id': transaction_id,
            'message': 'Payment processed and held in escrow'
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=405)

