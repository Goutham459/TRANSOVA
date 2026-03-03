import random
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from .models import User
from fleet.models import Company


def company_register(request):
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
        Company.objects.create(
            user=user,
            company_name=company_name,
            trade_license=trade_license,
            phone=phone,
            is_approved=False  # Requires admin approval
        )

        messages.success(request, "Company registration submitted! Please wait for admin approval.")
        return redirect('company_pending')

    return render(request, 'accounts/company_register.html')


def company_pending(request):
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


# REGISTER VIEW
def register(request):
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

        # Generate OTP and store registration data in session
        otp = random.randint(100000, 999999)
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
            "noreply@transova.com",  # you can replace with your EMAIL_HOST_USER
            [email],
        )

        return redirect("verify_otp")

    return render(request, "accounts/register.html")


# VERIFY OTP VIEW

def verify_otp(request):
    # Get the email from session data (set in register)
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

    # GET request → show the OTP form
    return render(request, "accounts/verify_otp.html", {"email": email})
