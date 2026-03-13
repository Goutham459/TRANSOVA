"""
================================================================================
ACCOUNTS APPLICATION VIEWS
================================================================================
This module contains all view functions for user authentication and management.

Views are organized into the following sections:
    1. Authentication (login, register, logout, password reset)
    2. Profile Management (customer, driver, company)
    3. Company Registration

Each view includes:
    - Docstring explaining purpose and functionality
    - Permission checks
    - Error handling

For settings, see: config/settings.py
================================================================================
"""

# ============================================================================
# DJANGO CORE IMPORTS
# ============================================================================
import logging
import random

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse

# Get DEBUG setting for conditional error messages
DEBUG = getattr(settings, "DEBUG", False)

from fleet.models import Company, Driver

# ============================================================================
# APPLICATION IMPORTS
# ============================================================================
from .models import User

# ============================================================================
# LOGGER CONFIGURATION
# ============================================================================
logger = logging.getLogger(__name__)


# =============================================================================
# SECTION 1: AUTHENTICATION VIEWS
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
        - Only Gmail addresses allowed (@gmail.com)
        - Email and username must be unique

    Validation:
        - Checks for existing email/username before OTP generation
        - Uses OTP for email verification
    """
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not username or not email or not password:
            messages.error(request, "All fields are required")
            return redirect("register")

        # Gmail-only check - enforce company policy
        if not email or not email.endswith("@gmail.com"):
            messages.error(request, "Only Gmail IDs are allowed")
            return redirect("register")

        # Check for existing email
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        # Check for existing username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already used")
            return redirect("register")

        # Generate 6-digit OTP
        otp = random.randint(100000, 999999)

        # Store OTP and registration data in session
        request.session["otp"] = otp
        request.session["reg_data"] = {
            "username": username,
            "email": email,
            "password": password,
        }

        # Send OTP via email
        try:
            send_mail(
                "Transova Email Verification",
                f"Your OTP is {otp}",
                "noreply@transova.com",
                [email],
            )
            logger.info(f"OTP sent successfully to {email}")
        except Exception as e:
            logger.error(f"Failed to send OTP email: {e}")
            # For debugging - show the actual error in development
            if DEBUG:
                messages.error(request, f"Failed to send verification email: {str(e)}")
            else:
                messages.error(
                    request, "Failed to send verification email. Please try again."
                )
            return redirect("register")

        return redirect("verify_otp")

    return render(request, "accounts/register.html")


def verify_otp(request):
    """
    OTP verification for registration.

    URL: /verify-otp/
    Template: accounts/verify_otp.html

    Validates OTP entered by user against session-stored OTP.
    On success, creates the user account and clears session data.
    """
    # Get stored registration data
    reg_data = request.session.get("reg_data")
    if not reg_data:
        messages.error(request, "Session expired. Please register again.")
        return redirect("register")

    email = reg_data.get("email")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("otp")

        if str(entered_otp) == str(session_otp):
            # OTP verified - create user account
            User.objects.create_user(
                username=reg_data["username"],
                email=reg_data["email"],
                password=reg_data["password"],
            )

            # Clear session data
            del request.session["otp"]
            del request.session["reg_data"]

            messages.success(request, "Registration successful! You can now log in.")
            return redirect("login")
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("verify_otp")

    return render(request, "accounts/verify_otp.html", {"email": email})


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
        Company cannot log in to dashboard until approved by admin.

    Fields:
        - email: Company email (username)
        - password: Account password
        - company_name: Business name
        - trade_license: License number
        - phone: Contact number
    """
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        company_name = request.POST.get("company_name")
        trade_license = request.POST.get("trade_license")
        phone = request.POST.get("phone")

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("company_register")

        # Create user with COMPANY role
        user = User.objects.create_user(
            username=email, email=email, password=password, role="COMPANY"
        )

        # Create company profile
        company = Company.objects.create(
            user=user,
            company_name=company_name,
            trade_license=trade_license,
            phone=phone,
            is_approved=False,  # Requires admin approval
        )

        # Send notification to admin
        from django.conf import settings

        admin_email = getattr(settings, "EMAIL_HOST_USER", "admin@transova.com")

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

        messages.success(
            request, "Company registration submitted! Please wait for admin approval."
        )
        return redirect("company_pending")

    return render(request, "accounts/company_register.html")


def company_pending(request):
    """
    Company pending approval page.

    URL: /company-pending/
    Template: accounts/company_pending.html

    Displayed when:
        - Company has registered but not yet approved
        - Company is waiting for admin verification

    Redirects to company dashboard if already approved.
    """
    if not request.user.is_authenticated:
        return redirect("login")

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect("login")

    if company.is_approved:
        return redirect("company_dashboard")

    return render(request, "accounts/company_pending.html", {"company": company})


# =============================================================================
# SECTION 2: PROFILE MANAGEMENT VIEWS
# =============================================================================


def customer_profile(request):
    """
    Customer profile view and update.

    URL: /customer-profile/ (or /profile/)
    Template: accounts/customer_profile.html

    Supports both regular form submission and AJAX requests for:
        - Photo update (profile_picture)
        - Personal info (first_name, last_name)
        - Contact info (email, phone, address)
        - Additional details (date_of_birth, gender)
        - Password change

    Access: Authenticated customers only
    """
    from django.http import JsonResponse
    from django.views.decorators.http import require_http_methods

    if not request.user.is_authenticated:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Please login to continue"}, status=401
            )
        return redirect("login")

    # Handle AJAX requests for individual field updates
    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        and request.method == "POST"
    ):
        update_type = request.POST.get("update_type", "")

        # Handle photo update
        if update_type == "photo":
            if "profile_picture" in request.FILES:
                request.user.profile_picture = request.FILES["profile_picture"]
                try:
                    request.user.save()
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Photo updated successfully!",
                            "new_photo_url": (
                                request.user.profile_picture.url
                                if request.user.profile_picture
                                else None
                            ),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating photo: {e}")
                    return JsonResponse(
                        {"success": False, "message": "Error updating photo"},
                        status=500,
                    )
            return JsonResponse({"success": False, "message": "No photo selected"})

        # Handle personal info update (name)
        elif update_type == "personal":
            request.user.first_name = request.POST.get("first_name", "")
            request.user.last_name = request.POST.get("last_name", "")
            try:
                request.user.save()
                return JsonResponse(
                    {"success": True, "message": "Name updated successfully!"}
                )
            except Exception as e:
                logger.error(f"Error updating name: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating name"}, status=500
                )

        # Handle contact info update
        elif update_type == "contact":
            request.user.email = request.POST.get("email", request.user.email)
            request.user.phone = request.POST.get("phone", "")
            request.user.address = request.POST.get("address", "")
            try:
                request.user.save()
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Contact information updated successfully!",
                    }
                )
            except Exception as e:
                logger.error(f"Error updating contact: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating contact info"},
                    status=500,
                )

        # Handle additional details update
        elif update_type == "additional":
            dob = request.POST.get("date_of_birth")
            if dob:
                request.user.date_of_birth = dob
            else:
                request.user.date_of_birth = None
            request.user.gender = request.POST.get("gender", "")
            try:
                request.user.save()
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Additional details updated successfully!",
                    }
                )
            except Exception as e:
                logger.error(f"Error updating additional details: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating details"}, status=500
                )

        # Handle password change
        elif update_type == "password":
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            # Validate current password
            if not request.user.check_password(current_password):
                return JsonResponse(
                    {"success": False, "message": "Current password is incorrect"}
                )

            # Validate new password length
            if len(new_password) < 8:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "New password must be at least 8 characters long",
                    }
                )

            # Check password confirmation
            if new_password != confirm_password:
                return JsonResponse(
                    {"success": False, "message": "New passwords do not match"}
                )

            try:
                request.user.set_password(new_password)
                request.user.save()
                # Re-authenticate the user after password change
                from django.contrib.auth import login

                login(request, request.user)
                return JsonResponse(
                    {"success": True, "message": "Password updated successfully!"}
                )
            except Exception as e:
                logger.error(f"Error updating password: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating password"}, status=500
                )

        return JsonResponse({"success": False, "message": "Invalid update type"})

    # Handle regular form submission (fallback)
    if request.method == "POST":
        # Check if this is a password change request
        if "current_password" in request.POST:
            # Handle password change
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            # Validate current password
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect("customer_profile")

            # Validate new password length
            if len(new_password) < 8:
                messages.error(
                    request, "New password must be at least 8 characters long."
                )
                return redirect("customer_profile")

            # Check password confirmation
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect("customer_profile")

            # Update password
            try:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(
                    request,
                    "Password updated successfully! Please log in again with your new password.",
                )
                # Re-authenticate the user after password change
                from django.contrib.auth import login

                login(request, request.user)
            except Exception as e:
                logger.error(f"Error updating password: {e}")
                messages.error(request, f"Error updating password: {e}")
                return redirect("customer_profile")

            return redirect("customer_profile")

        # Handle profile update (existing code)
        # Update user profile fields
        user = request.user
        user.first_name = request.POST.get("first_name", "")
        user.last_name = request.POST.get("last_name", "")
        user.email = request.POST.get("email", "")
        user.phone = request.POST.get("phone", "")
        user.address = request.POST.get("address", "")

        # Handle profile picture upload
        if "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]

        # Handle date of birth
        dob = request.POST.get("date_of_birth")
        if dob:
            user.date_of_birth = dob

        user.gender = request.POST.get("gender", "")

        try:
            user.save()
            messages.success(request, "Profile updated successfully!")
        except Exception as e:
            logger.error(f"Error updating customer profile: {e}")
            messages.error(request, f"Error updating profile: {e}")

        return redirect("customer_profile")

    return render(request, "accounts/customer_profile.html", {"user": request.user})


def driver_profile_update(request):
    """
    Driver profile view and update.

    URL: /driver-profile-update/
    Template: accounts/driver_profile.html

    Supports both regular form submission and AJAX requests for:
        - Driver photo update
        - User account photo update
        - Personal info (name, email, phone, address)
        - Driver details (license, experience)
        - Additional details (dob, gender)

    Access: Authenticated drivers only
    """
    from django.http import JsonResponse

    if not request.user.is_authenticated:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Please login to continue"}, status=401
            )
        return redirect("login")

    try:
        driver = Driver.objects.get(user=request.user)
    except Driver.DoesNotExist:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Driver profile not found"}, status=404
            )
        messages.error(request, "Driver profile not found.")
        return redirect("login")

    # Handle AJAX requests for individual field updates
    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        and request.method == "POST"
    ):
        update_type = request.POST.get("update_type", "")

        # Handle driver photo update
        if update_type == "driver_photo":
            if "driver_photo" in request.FILES:
                driver.profile_picture = request.FILES["driver_photo"]
                try:
                    driver.save()
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Driver photo updated successfully!",
                            "new_photo_url": (
                                driver.profile_picture.url
                                if driver.profile_picture
                                else None
                            ),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating driver photo: {e}")
                    return JsonResponse(
                        {"success": False, "message": "Error updating photo"},
                        status=500,
                    )
            return JsonResponse({"success": False, "message": "No photo selected"})

        # Handle user account photo update
        elif update_type == "user_photo":
            if "profile_picture" in request.FILES:
                request.user.profile_picture = request.FILES["profile_picture"]
                try:
                    request.user.save()
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Account photo updated successfully!",
                            "new_photo_url": (
                                request.user.profile_picture.url
                                if request.user.profile_picture
                                else None
                            ),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating user photo: {e}")
                    return JsonResponse(
                        {"success": False, "message": "Error updating photo"},
                        status=500,
                    )
            return JsonResponse({"success": False, "message": "No photo selected"})

        # Handle personal info update
        elif update_type == "personal":
            request.user.first_name = request.POST.get("first_name", "")
            request.user.last_name = request.POST.get("last_name", "")
            request.user.email = request.POST.get("email", request.user.email)
            request.user.phone = request.POST.get("phone", "")
            request.user.address = request.POST.get("address", "")
            try:
                request.user.save()
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Personal information updated successfully!",
                    }
                )
            except Exception as e:
                logger.error(f"Error updating personal info: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating info"}, status=500
                )

        # Handle driver details update
        elif update_type == "driver_details":
            driver.license_number = request.POST.get("license_number", "")
            driver.phone = request.POST.get("driver_phone", "")
            driver.address = request.POST.get("driver_address", "")

            license_expiry = request.POST.get("license_expiry")
            if license_expiry:
                driver.license_expiry = license_expiry
            else:
                driver.license_expiry = None

            experience = request.POST.get("experience_years")
            if experience:
                driver.experience_years = experience
            else:
                driver.experience_years = None

            try:
                driver.save()
                return JsonResponse(
                    {"success": True, "message": "Driver details updated successfully!"}
                )
            except Exception as e:
                logger.error(f"Error updating driver details: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating details"}, status=500
                )

        # Handle additional details update
        elif update_type == "additional":
            dob = request.POST.get("date_of_birth")
            if dob:
                request.user.date_of_birth = dob
            else:
                request.user.date_of_birth = None
            request.user.gender = request.POST.get("gender", "")
            try:
                request.user.save()
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Additional details updated successfully!",
                    }
                )
            except Exception as e:
                logger.error(f"Error updating additional details: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating details"}, status=500
                )

        return JsonResponse({"success": False, "message": "Invalid update type"})

    # Handle regular form submission (fallback)
    if request.method == "POST":
        # Update user fields
        user = request.user
        user.first_name = request.POST.get("first_name", "")
        user.last_name = request.POST.get("last_name", "")
        user.email = request.POST.get("email", "")
        user.phone = request.POST.get("phone", "")
        user.address = request.POST.get("address", "")

        # Handle profile picture (user profile)
        if "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]

        # Handle date of birth
        dob = request.POST.get("date_of_birth")
        if dob:
            user.date_of_birth = dob

        user.gender = request.POST.get("gender", "")
        user.save()

        # Update driver-specific fields
        driver.license_number = request.POST.get("license_number", "")
        driver.phone = request.POST.get("driver_phone", "")
        driver.address = request.POST.get("driver_address", "")

        license_expiry = request.POST.get("license_expiry")
        if license_expiry:
            driver.license_expiry = license_expiry

        experience = request.POST.get("experience_years")
        if experience:
            driver.experience_years = experience

        # Handle driver profile picture
        if "driver_photo" in request.FILES:
            driver.profile_picture = request.FILES["driver_photo"]

        try:
            driver.save()
            messages.success(request, "Profile updated successfully!")
        except Exception as e:
            logger.error(f"Error updating driver profile: {e}")
            messages.error(request, f"Error updating profile: {e}")

        return redirect("driver_profile_update")

    return render(
        request,
        "accounts/driver_profile.html",
        {"user": request.user, "driver": driver},
    )


def company_profile_update(request):
    """
    Company profile view and update.

    URL: /company-profile-update/
    Template: accounts/company_profile.html

    Supports both regular form submission and AJAX requests for:
        - Company logo update
        - Company information (name, phone, address, etc.)
        - Admin contact (name, phone)

    Access: Authenticated companies only
    """
    from django.http import JsonResponse

    if not request.user.is_authenticated:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Please login to continue"}, status=401
            )
        return redirect("login")

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Company profile not found"}, status=404
            )
        messages.error(request, "Company profile not found.")
        return redirect("login")

    # Handle AJAX requests for individual field updates
    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        and request.method == "POST"
    ):
        update_type = request.POST.get("update_type", "")

        # Handle logo update
        if update_type == "logo":
            if "logo" in request.FILES:
                company.logo = request.FILES["logo"]
                try:
                    company.save()
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Logo updated successfully!",
                            "new_logo_url": company.logo.url if company.logo else None,
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating logo: {e}")
                    return JsonResponse(
                        {"success": False, "message": "Error updating logo"}, status=500
                    )
            return JsonResponse({"success": False, "message": "No logo selected"})

        # Handle company info update
        elif update_type == "company_info":
            company.company_name = request.POST.get(
                "company_name", company.company_name
            )
            company.phone = request.POST.get("phone", company.phone)
            company.address = request.POST.get("address", company.address)
            company.trade_license = request.POST.get(
                "trade_license", company.trade_license
            )
            company.description = request.POST.get("description", company.description)
            company.website = request.POST.get("website", company.website)
            company.contact_person = request.POST.get(
                "contact_person", company.contact_person
            )

            try:
                company.save()
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Company information updated successfully!",
                    }
                )
            except Exception as e:
                logger.error(f"Error updating company info: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating info"}, status=500
                )

        # Handle admin contact update
        elif update_type == "admin_contact":
            request.user.first_name = request.POST.get("first_name", "")
            request.user.last_name = request.POST.get("last_name", "")
            request.user.phone = request.POST.get("user_phone", "")

            try:
                request.user.save()
                return JsonResponse(
                    {"success": True, "message": "Admin contact updated successfully!"}
                )
            except Exception as e:
                logger.error(f"Error updating admin contact: {e}")
                return JsonResponse(
                    {"success": False, "message": "Error updating contact"}, status=500
                )

        return JsonResponse({"success": False, "message": "Invalid update type"})

    # Handle regular form submission (fallback)
    if request.method == "POST":
        # Update company fields
        company.company_name = request.POST.get("company_name", company.company_name)
        company.phone = request.POST.get("phone", company.phone)
        company.address = request.POST.get("address", company.address)
        company.trade_license = request.POST.get("trade_license", company.trade_license)
        company.description = request.POST.get("description", company.description)
        company.website = request.POST.get("website", company.website)
        company.contact_person = request.POST.get(
            "contact_person", company.contact_person
        )

        # Handle logo upload
        if "logo" in request.FILES:
            company.logo = request.FILES["logo"]

        # Update user fields
        user = request.user
        user.first_name = request.POST.get("first_name", "")
        user.last_name = request.POST.get("last_name", "")
        user.phone = request.POST.get("user_phone", "")

        try:
            company.save()
            user.save()
            messages.success(request, "Company profile updated successfully!")
        except Exception as e:
            logger.error(f"Error updating company profile: {e}")
            messages.error(request, f"Error updating profile: {e}")

        return redirect("company_profile_update")

    return render(
        request,
        "accounts/company_profile.html",
        {"user": request.user, "company": company},
    )


# =============================================================================
# SECTION 3: PASSWORD MANAGEMENT
# =============================================================================


def resend_otp(request):
    """
    Resend OTP for email verification.

    URL: /resend-otp/

    Used during registration when user needs a new OTP.
    """
    otp = random.randint(100000, 999999)
    request.session["otp"] = otp

    reg_data = request.session.get("reg_data", {})
    email = reg_data.get("email", "")

    if email:
        try:
            send_mail(
                "Transova OTP Verification",
                f"Your new OTP is {otp}",
                "noreply@transova.com",
                [email],
            )
        except Exception as e:
            logger.error(f"Failed to resend OTP: {e}")
            messages.error(request, "Failed to send OTP. Please try again.")
    else:
        messages.error(request, "Session expired. Please register again.")
        return redirect("register")

    return redirect("verify_otp")


def forgot_password(request):
    """
    Forgot password - initiates password reset flow.

    URL: /forgot-password/
    Template: accounts/forgot_password.html

    Flow:
        1. User enters registered email
        2. OTP is sent to their email
        3. User enters OTP + new password

    Validation:
        - Checks if email exists in system
    """
    if request.method == "POST":
        email = request.POST.get("email")

        if not User.objects.filter(email=email).exists():
            messages.error(request, "Email not registered")
            return redirect("forgot_password")

        # Generate and store OTP
        otp = random.randint(100000, 999999)
        request.session["reset_otp"] = otp
        request.session["reset_email"] = email

        try:
            send_mail(
                "Transova Password Reset",
                f"Your OTP is {otp}",
                "noreply@transova.com",
                [email],
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            messages.error(request, "Failed to send reset email. Please try again.")
            return redirect("forgot_password")

        return redirect("reset_password")

    return render(request, "accounts/forgot_password.html")


def reset_password(request):
    """
    Reset password using OTP verification.

    URL: /reset-password/
    Template: accounts/reset_password.html

    Requires:
        - Valid OTP from session
        - New password confirmation
    """
    if request.method == "POST":
        session_otp = request.session.get("reset_otp")
        session_email = request.session.get("reset_email")
        entered_otp = request.POST.get("otp")

        if not session_otp or not session_email:
            messages.error(
                request, "Session expired. Please start password reset again."
            )
            return redirect("forgot_password")

        if int(entered_otp) == session_otp:
            try:
                user = User.objects.get(email=session_email)
                user.set_password(request.POST.get("password"))
                user.save()

                # Clear session
                request.session.pop("reset_otp", None)
                request.session.pop("reset_email", None)

                messages.success(request, "Password reset successful! Please log in.")
                return redirect("login")
            except Exception as e:
                logger.error(f"Error resetting password: {e}")
                messages.error(request, "Error resetting password. Please try again.")
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("reset_password")

    return render(request, "accounts/reset_password.html")


# =============================================================================
# EXPORT STATEMENTS
# =============================================================================
__all__ = [
    "register",
    "verify_otp",
    "company_register",
    "company_pending",
    "customer_profile",
    "driver_profile_update",
    "company_profile_update",
    "resend_otp",
    "forgot_password",
    "reset_password",
]
