import math
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib.auth.views import LoginView
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from .models import Booking
from fleet.models import Truck, Company
from pricing.models import LoadType
import random
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Booking
import requests


# ---------------- HOME ----------------
def home(request):
    trucks = Truck.objects.filter(is_available=True)
    load_types = LoadType.objects.all()
    return render(request, "bookings/home.html", {
        "trucks": trucks,
        "load_types": load_types
    })


# ---------------- BOOKINGS ----------------
def booking_list(request):
    bookings = Booking.objects.all().order_by("-booking_date")
    return render(request, "bookings/booking_list.html", {"bookings": bookings})


def add_booking(request):
    trucks = Truck.objects.all()
    load_types = LoadType.objects.all()

    if request.method == "POST":
        truck = Truck.objects.get(id=request.POST.get("truck"))
        load_type = LoadType.objects.get(id=request.POST.get("load_type"))
        distance_km = float(request.POST.get("distance_km"))

        BASE_PRICE = 50
        RATE_PER_KM = 10
        price = (BASE_PRICE + distance_km * RATE_PER_KM) * load_type.price_multiplier

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

        truck.is_available = False
        truck.save()

        return redirect("add_booking")

    return render(request, "bookings/add_booking.html", {
        "trucks": trucks,
        "load_types": load_types
    })


def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    trucks = Truck.objects.filter(is_available=True) | Truck.objects.filter(id=booking.truck.id)
    load_types = LoadType.objects.all()

    if request.method == "POST":
        booking.customer_name = request.POST.get("customer_name")
        booking.pickup_location = request.POST.get("pickup_location")
        booking.drop_location = request.POST.get("drop_location")
        booking.booking_date = request.POST.get("booking_date")
        booking.distance_km = float(request.POST.get("distance_km"))

        booking.truck = Truck.objects.get(id=request.POST.get("truck"))
        booking.load_type = LoadType.objects.get(id=request.POST.get("load_type"))

        BASE_PRICE = 50
        RATE_PER_KM = 10
        booking.price = (
            BASE_PRICE + booking.distance_km * RATE_PER_KM
        ) * booking.load_type.price_multiplier

        booking.save()
        return redirect("booking_list")

    return render(request, "bookings/edit_booking.html", {
        "booking": booking,
        "trucks": trucks,
        "load_types": load_types
    })


def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    truck = booking.truck
    booking.delete()

    truck.is_available = True
    truck.save()

    return redirect("booking_list")


# ---------------- DASHBOARD ----------------
def dashboard(request):
    return render(request, "bookings/dashboard.html", {
        "total_bookings": Booking.objects.count(),
        "total_revenue": Booking.objects.aggregate(Sum("price"))["price__sum"] or 0,
        "recent_bookings": Booking.objects.order_by("-booking_date")[:5],
    })


# ---------------- CUSTOMER DASHBOARD ----------------
@login_required(login_url='/login/')
def customer_dashboard(request):
    if request.user.role != 'CUSTOMER':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    user_bookings = Booking.objects.filter(
        customer_name=request.user.get_full_name() or request.user.username
    ).order_by("-booking_date")[:10]
    
    context = {
        'bookings': user_bookings,
        'total_bookings': user_bookings.count(),
    }
    return render(request, "bookings/customer_dashboard.html", context)


# ---------------- ADMIN DASHBOARD ----------------
@login_required(login_url='/login/')
def admin_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    context = {
        'total_bookings': Booking.objects.count(),
        'total_revenue': Booking.objects.aggregate(Sum("price"))["price__sum"] or 0,
        'recent_bookings': Booking.objects.order_by("-booking_date")[:10],
        'pending_companies': Company.objects.filter(is_approved=False).count(),
    }
    return render(request, "bookings/admin_dashboard.html", context)


# ---------------- DRIVER DASHBOARD ----------------
@login_required(login_url='/login/')
def driver_dashboard(request):
    if request.user.role != 'DRIVER':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    context = {
        'driver': request.user,
    }
    return render(request, "bookings/driver_dashboard.html", context)


# ---------------- CUSTOMER BOOKING ----------------
def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two lat/lng points in km"""
    R = 6371  # Earth radius in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


@login_required(login_url='/login/')
def customer_booking(request):
    trucks = Truck.objects.filter(is_available=True)
    load_types = LoadType.objects.all()

    if request.method == "POST" and request.is_ajax():
        # Get form data
        customer_name = request.POST.get("customer_name")
        contact_number = request.POST.get("contact_number")
        pickup_location = request.POST.get("pickup_location")
        drop_location = request.POST.get("drop_location")
        booking_date = request.POST.get("booking_date")

        # Pickup / Drop lat/lng
        pickup_lat = float(request.POST.get("pickup_lat"))
        pickup_lng = float(request.POST.get("pickup_lng"))
        drop_lat = float(request.POST.get("drop_lat"))
        drop_lng = float(request.POST.get("drop_lng"))

        # Calculate distance
        distance_km = haversine(pickup_lat, pickup_lng, drop_lat, drop_lng)

        # Base rate & commission
        BASE_RATE = 2  # $ per km
        price = distance_km * BASE_RATE
        total_price = round(price * 1.05, 2)  # add 5% commission

        # Detect currency
        ip_info = requests.get('https://ipapi.co/json/').json()
        currency = ip_info.get('currency', 'USD')

        # Optional: assign first available truck
        truck = trucks.first() if trucks.exists() else None
        if truck:
            truck.is_available = False
            truck.save()

        # Optional: assign default load type (or let user select)
        load_type = load_types.first() if load_types.exists() else None

        # Create booking
        booking = Booking.objects.create(
            customer_name=customer_name,
            contact_number=contact_number,
            pickup_location=pickup_location,
            drop_location=drop_location,
            booking_date=booking_date,
            distance_km=distance_km,
            price=total_price,
            currency=currency,
            truck=truck,
            load_type=load_type
        )

        return JsonResponse({
            "success": True,
            "amount": total_price,
            "currency": currency,
            "booking_id": booking.id
        })

    return render(request, "bookings/customer_booking.html", {
        "trucks": trucks,
        "load_types": load_types
    })


def book_truck(request):
    if request.method == "POST":
        customer_name = request.POST.get("customer_name")
        contact_number = request.POST.get("contact_number")
        pickup_location = request.POST.get("pickup_location")
        drop_location = request.POST.get("drop_location")
        booking_date = request.POST.get("booking_date")

        # Use Google Maps API to calculate distance server-side if you want
        # For simplicity, we'll use a dummy distance
        distance_km = 10  # replace with API calculation
        base_rate = 2
        price = distance_km * base_rate
        total_price = price + price * 0.05

        # Detect currency
        ip_info = requests.get('https://ipapi.co/json/').json()
        currency = ip_info.get('currency', 'USD')

        booking = Booking.objects.create(
            customer_name=customer_name,
            contact_number=contact_number,
            pickup_location=pickup_location,
            drop_location=drop_location,
            booking_date=booking_date,
            total_price=total_price,
            currency=currency
        )

        return JsonResponse({
            "success": True,
            "amount": total_price,
            "currency": currency,
            "booking_id": booking.id
        })

    return render(request, 'bookings/book_truck.html')


# ---------------- TRUCK LIST ----------------
def trucks_list(request):
    trucks = Truck.objects.all()

    if request.GET.get("type"):
        trucks = trucks.filter(truck_type__iexact=request.GET["type"])

    if request.GET.get("load"):
        trucks = trucks.filter(load_types__id=request.GET["load"])

    if request.GET.get("availability") == "available":
        trucks = trucks.filter(is_available=True)
    elif request.GET.get("availability") == "booked":
        trucks = trucks.filter(is_available=False)

    return render(request, "bookings/trucks_list.html", {
        "trucks": trucks,
        "load_types": LoadType.objects.all(),
        "truck_types": Truck.objects.values_list("truck_type", flat=True).distinct(),
        "selected_type": request.GET.get("type"),
        "selected_load": request.GET.get("load"),
        "selected_availability": request.GET.get("availability"),
    })


# ---------------- AUTH ----------------
class RoleBasedLoginView(LoginView):
    template_name = "accounts/login.html"

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


def resend_otp(request):
    import random
    otp = random.randint(100000, 999999)
    request.session["otp"] = otp

    send_mail(
        "Transova OTP Verification",
        f"Your new OTP is {otp}",
        "noreply@transova.com",
        [request.session["reg_data"]["email"]],
    )
    return redirect("verify_otp")


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not User.objects.filter(email=email).exists():
            messages.error(request, "Email not registered")
            return redirect("forgot_password")

        otp = random.randint(100000, 999999)
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
    if request.method == "POST":
        if int(request.POST.get("otp")) == request.session.get("reset_otp"):
            user = User.objects.get(email=request.session["reset_email"])
            user.set_password(request.POST.get("password"))
            user.save()
            return redirect("login")

    return render(request, "accounts/reset_password.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# ---------------- PAYMENT ----------------
def payment(request):
    amount = request.GET.get('amount', 0)
    currency = request.GET.get('currency', 'USD')
    booking_id = request.GET.get('booking_id', None)
    
    context = {
        'amount': amount,
        'currency': currency,
        'booking_id': booking_id,
    }
    return render(request, "bookings/payment.html", context)


def payment_success(request):
    booking_id = request.GET.get('booking_id')
    if booking_id:
        try:
            booking = Booking.objects.get(id=booking_id)
            # Update booking status or create payment record
            booking.save()
        except Booking.DoesNotExist:
            pass
    
    return render(request, "bookings/payment_success.html")


def payment_cancel(request):
    booking_id = request.GET.get('booking_id')
    if booking_id:
        try:
            booking = Booking.objects.get(id=booking_id)
            # Release the truck back to available
            if booking.truck:
                booking.truck.is_available = True
                booking.truck.save()
            booking.delete()
        except Booking.DoesNotExist:
            pass
    
    return render(request, "bookings/payment_cancel.html")


# ==================== CUSTOM ADMIN PANEL VIEWS ====================

@login_required(login_url='/login/')
def admin_users(request):
    """Manage all users"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from accounts.models import User
    users = User.objects.all().order_by('-date_joined')
    return render(request, "bookings/admin_users.html", {"users": users})


@login_required(login_url='/login/')
def admin_user_detail(request, user_id):
    """View user details"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from accounts.models import User
    user = get_object_or_404(User, id=user_id)
    return render(request, "bookings/admin_user_detail.html", {"user_obj": user})


@login_required(login_url='/login/')
def admin_user_delete(request, user_id):
    """Delete a user"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from accounts.models import User
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect('admin_users')
    
    return render(request, "bookings/admin_user_delete.html", {"user_obj": user})


@login_required(login_url='/login/')
def admin_trucks(request):
    """Manage all trucks"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Truck
    trucks = Truck.objects.all().order_by('-created_at')
    return render(request, "bookings/admin_trucks.html", {"trucks": trucks})


@login_required(login_url='/login/')
def admin_truck_add(request):
    """Add a new truck (Admin)"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Truck, Company
    
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
    """Edit a truck"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Truck
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
    """Delete a truck"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Truck
    truck = get_object_or_404(Truck, id=truck_id)
    
    if request.method == 'POST':
        truck.delete()
        messages.success(request, "Truck deleted successfully.")
        return redirect('admin_trucks')
    
    return render(request, "bookings/admin_truck_delete.html", {"truck": truck})


@login_required(login_url='/login/')
def admin_companies(request):
    """Manage all companies"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Company
    companies = Company.objects.all().order_by('-created_at')
    return render(request, "bookings/admin_companies.html", {"companies": companies})


@login_required(login_url='/login/')
def admin_company_approve(request, company_id):
    """Approve a company"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Company
    company = get_object_or_404(Company, id=company_id)
    company.is_approved = True
    company.save()
    
    # Send approval email to company
    try:
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
        # Log error but don't interrupt the flow
        print(f"Email sending failed: {e}")
    
    messages.success(request, f"Company '{company.company_name}' approved successfully.")
    return redirect('admin_companies')


@login_required(login_url='/login/')
def admin_company_disapprove(request, company_id):
    """Disapprove a company"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Company
    company = get_object_or_404(Company, id=company_id)
    company.is_approved = False
    company.save()
    
    # Send rejection email to company
    try:
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
        # Log error but don't interrupt the flow
        print(f"Email sending failed: {e}")
    
    messages.success(request, f"Company '{company.company_name}' disapproved.")
    return redirect('admin_companies')


@login_required(login_url='/login/')
def company_status_check(request):
    """API endpoint for company to check their approval status"""
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


@login_required(login_url='/login/')
def admin_drivers(request):
    """Manage all drivers"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from fleet.models import Driver
    drivers = Driver.objects.all()
    return render(request, "bookings/admin_drivers.html", {"drivers": drivers})


@login_required(login_url='/login/')
def admin_load_types(request):
    """Manage all load types"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from pricing.models import LoadType
    load_types = LoadType.objects.all()
    return render(request, "bookings/admin_load_types.html", {"load_types": load_types})


@login_required(login_url='/login/')
def admin_load_type_add(request):
    """Add a new load type"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from pricing.models import LoadType
    
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
    """Edit a load type"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from pricing.models import LoadType
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
    """Delete a load type"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from pricing.models import LoadType
    load_type = get_object_or_404(LoadType, id=load_type_id)
    
    if request.method == 'POST':
        load_type.delete()
        messages.success(request, "Load type deleted successfully.")
        return redirect('admin_load_types')
    
    return render(request, "bookings/admin_load_type_delete.html", {"load_type": load_type})


@login_required(login_url='/login/')
def admin_subscriptions(request):
    """Manage all subscriptions"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')
    
    from pricing.models import Subscription
    subscriptions = Subscription.objects.all().order_by('-start_date')
    return render(request, "bookings/admin_subscriptions.html", {"subscriptions": subscriptions})


@login_required(login_url='/login/')
def admin_subscription_toggle(request, subscription_id):
    """Toggle subscription active status"""
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


@login_required(login_url='/login/')
def admin_stats(request):
    """Get admin statistics as JSON"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    
    from accounts.models import User
    from fleet.models import Truck, Company, Driver
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
