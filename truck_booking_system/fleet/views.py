"""
================================================================================
FLEET APPLICATION VIEWS
================================================================================
This module contains all view functions for the fleet management application.

Views are organized into the following sections:
    1. Company Dashboard
    2. Truck Management
    3. Driver Management
    4. Booking Management

Each view includes:
    - Docstring explaining purpose and functionality
    - Permission checks
    - Error handling
    - Query optimizations with select_related/prefetch_related

For settings, see: config/settings.py
================================================================================
"""

# ============================================================================
# DJANGO CORE IMPORTS
# ============================================================================
import logging
from typing import Optional

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

# ============================================================================
# APPLICATION IMPORTS
# ============================================================================
from .models import Company, Truck, Driver
from bookings.models import Booking

# Get the custom user model
User = get_user_model()

# ============================================================================
# LOGGER CONFIGURATION
# ============================================================================
logger = logging.getLogger(__name__)


# =============================================================================
# SECTION 1: COMPANY DASHBOARD
# =============================================================================

@login_required
def company_dashboard(request):
    """
    Company dashboard - shows company overview and statistics.
    
    URL: /fleet/dashboard/
    Template: fleet/company_dashboard.html
    
    Displays:
        - Company information
        - Trucks (total and available)
        - Drivers with statistics
        - Recent bookings
        - Revenue statistics (total and this month)
    
    Access: Company users only (role='COMPANY' and approved)
    
    Query Optimization:
        - Uses select_related() for foreign keys
        - Aggregates are computed efficiently
    """
    # PERMISSION CHECK: Only companies can access this dashboard
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    # Check if company is approved
    if not company.is_approved:
        return redirect('company_pending')

    # GET COMPANY TRUCKS
    trucks = Truck.objects.filter(company=company)
    
    # GET COMPANY DRIVERS with statistics - Using select_related to avoid N+1 queries
    drivers = Driver.objects.filter(company=company).select_related('user', 'assigned_truck')
    
    # Calculate driver statistics efficiently
    driver_stats = []
    for driver in drivers:
        # Get all bookings for this driver
        driver_bookings = Booking.objects.filter(driver=driver)
        
        # Aggregate statistics
        total_km = driver_bookings.aggregate(Sum('distance_km'))['distance_km__sum'] or 0
        jobs_accepted = driver_bookings.count()
        jobs_completed = driver_bookings.filter(status='COMPLETED').count()
        
        driver_stats.append({
            'driver': driver,
            'total_km': total_km,
            'jobs_accepted': jobs_accepted,
            'jobs_completed': jobs_completed
        })
    
    # CALCULATE STATISTICS
    available_trucks = trucks.filter(is_available=True).count()
    
    # Get company bookings (from trucks assigned to this company)
    company_bookings = Booking.objects.filter(
        truck__company=company
    ).select_related('truck', 'driver__user').order_by('-booking_date')
    
    # Revenue calculations
    total_revenue = company_bookings.aggregate(Sum('price'))['price__sum'] or 0
    
    # This month's revenue
    today = datetime.now()
    month_start = today.replace(day=1)
    this_month_revenue = company_bookings.filter(
        booking_date__gte=month_start.date()
    ).aggregate(Sum('price'))['price__sum'] or 0
    
    # Booking counts
    total_bookings = company_bookings.count()
    completed_bookings = company_bookings.filter(truck__isnull=False).count()
    pending_bookings = company_bookings.filter(truck__isnull=True).count()
    
    # Get recent bookings for display (slice after all filters)
    recent_bookings = company_bookings[:10]
    
    context = {
        'company': company,
        'trucks': trucks,
        'driver_stats': driver_stats,
        'available_trucks': available_trucks,
        'company_bookings': recent_bookings,
        'total_revenue': total_revenue,
        'this_month_revenue': this_month_revenue,
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'pending_bookings': pending_bookings,
    }
    return render(request, 'fleet/company_dashboard.html', context)


@login_required
def company_pending(request):
    """
    Company pending approval page.
    
    URL: /fleet/pending/
    Template: fleet/company_pending.html
    
    Displayed when:
        - Company has registered but not yet approved
        - Company is waiting for admin verification
    
    Redirects to dashboard if already approved.
    """
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return redirect('login')
    
    if company.is_approved:
        return redirect('company_dashboard')
    
    return render(request, 'fleet/company_pending.html', {'company': company})


# =============================================================================
# SECTION 2: TRUCK MANAGEMENT
# =============================================================================

@login_required
def add_truck(request):
    """
    Add a new truck to the company fleet.
    
    URL: /fleet/add-truck/
    Template: fleet/add_truck.html
    
    Access: Company users only
    
    Fields:
        - truck_number: Unique identifier
        - truck_type: Type of truck
        - capacity: Load capacity
        - price_per_km: Pricing
        - image: Truck photo
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to add trucks.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    if not company.is_approved:
        messages.error(request, "Your company is not approved yet.")
        return redirect('company_pending')

    if request.method == 'POST':
        truck_number = request.POST.get('truck_number')
        truck_type = request.POST.get('truck_type')
        capacity = request.POST.get('capacity')
        price_per_km = request.POST.get('price_per_km')
        image = request.FILES.get('image')

        # Create truck with company association
        truck = Truck.objects.create(
            company=company,
            truck_number=truck_number,
            truck_type=truck_type,
            capacity=capacity,
            price_per_km=price_per_km,
            image=image,
            is_available=True
        )
        
        logger.info(f"Truck {truck_number} created by company {company.company_name}")
        
        messages.success(request, "Truck added successfully!")
        return redirect('company_dashboard')

    truck_types = Truck.TRUCK_TYPES
    return render(request, 'fleet/add_truck.html', {'truck_types': truck_types})


@login_required
def edit_truck(request, truck_id):
    """
    Edit existing truck details.
    
    URL: /fleet/edit-truck/<truck_id>/
    Template: fleet/edit_truck.html
    
    Access: Company users (only for their own trucks)
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to edit trucks.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    # Get truck belonging to this company only
    truck = get_object_or_404(Truck, id=truck_id, company=company)

    if request.method == 'POST':
        truck.truck_number = request.POST.get('truck_number')
        truck.truck_type = request.POST.get('truck_type')
        truck.capacity = request.POST.get('capacity')
        truck.price_per_km = request.POST.get('price_per_km')
        
        if request.FILES.get('image'):
            truck.image = request.FILES.get('image')
        
        truck.save()
        
        logger.info(f"Truck {truck.truck_number} updated by company {company.company_name}")
        
        messages.success(request, "Truck updated successfully!")
        return redirect('company_dashboard')

    truck_types = Truck.TRUCK_TYPES
    return render(request, 'fleet/edit_truck.html', {'truck': truck, 'truck_types': truck_types})


@login_required
def delete_truck(request, truck_id):
    """
    Delete a truck from the fleet.
    
    URL: /fleet/delete-truck/<truck_id>/
    
    Access: Company users (only for their own trucks)
    
    Warning: This action cannot be undone.
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to delete trucks.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    truck = get_object_or_404(Truck, id=truck_id, company=company)
    truck_number = truck.truck_number
    
    truck.delete()
    
    logger.info(f"Truck {truck_number} deleted by company {company.company_name}")
    
    messages.success(request, "Truck deleted successfully!")
    return redirect('company_dashboard')


# =============================================================================
# SECTION 3: DRIVER MANAGEMENT
# =============================================================================

@login_required
def add_driver(request):
    """
    Add a new driver to the company.
    
    URL: /fleet/add-driver/
    Template: fleet/add_driver.html
    
    Access: Company users only
    
    Creates:
        1. User account with DRIVER role
        2. Driver profile linked to company
    
    Note:
        Driver will need separate login credentials.
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to add drivers.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    if not company.is_approved:
        messages.error(request, "Your company is not approved yet.")
        return redirect('company_pending')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('add_driver')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('add_driver')

        try:
            # Create user with DRIVER role
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='DRIVER'
            )

            # Create driver profile for the company
            driver = Driver.objects.create(
                user=user,
                company=company
            )
            
            logger.info(f"Driver {username} created by company {company.company_name}")

            messages.success(request, f"Driver '{username}' added successfully!")
            return redirect('company_dashboard')
            
        except Exception as e:
            logger.error(f"Error creating driver: {e}")
            messages.error(request, f"Error adding driver: {str(e)}")
            return redirect('add_driver')

    # Get available trucks for assignment
    trucks = Truck.objects.filter(company=company, is_available=True)

    return render(request, 'fleet/add_driver.html', {'trucks': trucks})


@login_required
def edit_driver(request, driver_id):
    """
    Edit driver's details.
    
    URL: /fleet/edit-driver/<driver_id>/
    Template: fleet/edit_driver.html
    
    Access: Company users (only for their own drivers)
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to edit drivers.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    # Get driver belonging to this company
    driver = get_object_or_404(Driver, id=driver_id, company=company)

    if request.method == 'POST':
        # Update user fields
        driver.user.first_name = request.POST.get('first_name', '')
        driver.user.last_name = request.POST.get('last_name', '')
        driver.user.email = request.POST.get('email', '')
        driver.user.save()
        
        # Update driver fields
        driver.license_number = request.POST.get('license_number', '')
        driver.phone = request.POST.get('phone', '')
        driver.address = request.POST.get('address', '')
        driver.experience_years = request.POST.get('experience_years', 0)
        
        if request.POST.get('license_expiry'):
            driver.license_expiry = request.POST.get('license_expiry')
        if request.POST.get('date_of_birth'):
            driver.date_of_birth = request.POST.get('date_of_birth')
            
        driver.is_available = request.POST.get('is_available') == 'on'
        
        # Handle truck assignment
        truck_id = request.POST.get('assigned_truck')
        if truck_id:
            try:
                driver.assigned_truck = Truck.objects.get(id=truck_id, company=company)
            except Truck.DoesNotExist:
                driver.assigned_truck = None
        else:
            driver.assigned_truck = None
            
        driver.save()
        
        logger.info(f"Driver {driver.user.username} updated by company {company.company_name}")
        
        messages.success(request, f"Driver '{driver.user.username}' updated successfully!")
        return redirect('company_dashboard')

    # Get available trucks for assignment
    trucks = Truck.objects.filter(company=company)
    
    return render(request, 'fleet/edit_driver.html', {
        'driver': driver,
        'trucks': trucks
    })


@login_required
def delete_driver(request, driver_id):
    """
    Delete a driver from the company.
    
    URL: /fleet/delete-driver/<driver_id>/
    
    Access: Company users (only for their own drivers)
    
    Warning: This deletes both the driver profile and user account.
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to delete drivers.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    driver = get_object_or_404(Driver, id=driver_id, company=company)
    driver_user = driver.user
    driver_username = driver_user.username if driver_user else "Unknown"
    
    # Delete the driver profile
    driver.delete()
    
    # Delete the user account
    if driver_user:
        driver_user.delete()
    
    logger.info(f"Driver {driver_username} deleted by company {company.company_name}")
    
    messages.success(request, "Driver deleted successfully!")
    return redirect('company_dashboard')


# =============================================================================
# SECTION 4: BOOKING MANAGEMENT
# =============================================================================

@login_required
def company_bookings(request):
    """
    View all bookings for company's trucks.
    
    URL: /fleet/bookings/
    Template: fleet/company_bookings.html
    
    Access: Company users only
    
    Features:
        - Filter by booking status
        - Shows driver assignment status
        - Quick stats display
    
    Filters:
        - status: pending_assignment, assigned, accepted, rejected, in_progress, completed
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    if not company.is_approved:
        return redirect('company_pending')

    # Get all bookings for company's trucks with optimized queries
    company_bookings = Booking.objects.filter(
        truck__company=company
    ).select_related(
        'truck', 
        'driver', 
        'driver__user'
    ).order_by('-booking_date')
    
    # Apply status filter from query params
    status_filter = request.GET.get('status', '')
    if status_filter == 'pending_assignment':
        company_bookings = company_bookings.filter(driver__isnull=True)
    elif status_filter == 'assigned':
        company_bookings = company_bookings.filter(driver__isnull=False, driver_status='ASSIGNED')
    elif status_filter == 'accepted':
        company_bookings = company_bookings.filter(driver_status='ACCEPTED')
    elif status_filter == 'rejected':
        company_bookings = company_bookings.filter(driver_status='REJECTED')
    elif status_filter == 'in_progress':
        company_bookings = company_bookings.filter(status='IN_PROGRESS')
    elif status_filter == 'completed':
        company_bookings = company_bookings.filter(status='COMPLETED')
    
    # Get available drivers for assignment
    drivers = Driver.objects.filter(company=company, is_available=True)
    
    # Calculate stats
    pending_count = company_bookings.filter(driver__isnull=True).count()
    assigned_count = company_bookings.filter(driver__isnull=False).count()
    in_progress_count = company_bookings.filter(status='IN_PROGRESS').count()
    completed_count = company_bookings.filter(status='COMPLETED').count()
    
    context = {
        'company': company,
        'bookings': company_bookings,
        'drivers': drivers,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'assigned_count': assigned_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
    }
    return render(request, 'fleet/company_bookings.html', context)


@login_required
def company_booking_detail(request, booking_id):
    """
    View booking details and assign driver.
    
    URL: /fleet/booking/<booking_id>/
    Template: fleet/company_booking_detail.html
    
    Access: Company users only
    
    Features:
        - View complete booking information
        - Assign/reassign driver to booking
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    if not company.is_approved:
        return redirect('company_pending')

    # Get booking belonging to this company
    booking = get_object_or_404(
        Booking, 
        id=booking_id, 
        truck__company=company
    )
    
    # Get available drivers for this company
    drivers = Driver.objects.filter(company=company, is_available=True)
    
    context = {
        'company': company,
        'booking': booking,
        'drivers': drivers,
    }
    return render(request, 'fleet/company_booking_detail.html', context)


@login_required
def assign_driver_to_booking(request, booking_id):
    """
    Assign a driver to a booking.
    
    URL: /fleet/booking/<booking_id>/assign-driver/
    Method: POST
    
    Access: Company users only
    
    POST Data:
        - driver_id: ID of the driver to assign
    
    Action:
        - Sets driver assignment
        - Updates driver_status to 'ASSIGNED'
        - Records assignment timestamp
    """
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    if not company.is_approved:
        return redirect('company_pending')

    booking = get_object_or_404(Booking, id=booking_id, truck__company=company)
    
    if request.method == 'POST':
        driver_id = request.POST.get('driver_id')
        
        if not driver_id:
            messages.error(request, "Please select a driver.")
            return redirect('company_booking_detail', booking_id=booking_id)
        
        try:
            driver = Driver.objects.get(id=driver_id, company=company)
        except Driver.DoesNotExist:
            messages.error(request, "Driver not found.")
            return redirect('company_booking_detail', booking_id=booking_id)
        
        # Assign driver to booking
        booking.driver = driver
        booking.driver_status = 'ASSIGNED'
        booking.assigned_at = timezone.now()
        booking.save()
        
        logger.info(f"Driver {driver.user.username} assigned to booking {booking.id} by company {company.company_name}")
        
        messages.success(request, f"Driver '{driver.user.get_full_name()}' assigned successfully!")
        return redirect('company_bookings')
    
    return redirect('company_booking_detail', booking_id=booking_id)

