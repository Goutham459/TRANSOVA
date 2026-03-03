from django.urls import path, include
from bookings.views import (
    forgot_password,
    home,
    logout_view,
    reset_password,
    trucks_list,
    RoleBasedLoginView,
    add_booking,
    payment,
    admin_dashboard
)
from accounts.views import register, verify_otp, company_register
from config import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", home, name="home"),
    path("trucks/", trucks_list, name="trucks_list"),
    
    # Custom Admin Panel (replaces default Django admin)
    path("admin/", admin_dashboard, name="custom_admin"),
    path("bookings/admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    
    path("bookings/", include("bookings.urls")),
    path("accounts/", include("accounts.urls")),
    path("fleet/", include("fleet.urls")),
    path("pricing/", include("pricing.urls")),

    # Auth - Custom login before allauth
    path("login/", RoleBasedLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("accounts/", include("allauth.urls")),
    path("register/", register, name="register"),
    path("forgot-password/", forgot_password, name="forgot_password"),
    path("reset-password/", reset_password, name="reset_password"),
    path("company-register/", company_register, name="company_register"),
    path("payment/", payment, name="payment"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
