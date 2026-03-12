from django.urls import path, include, re_path
from django.views.generic import RedirectView
from bookings.views import (
    forgot_password,
    home,
    logout_view,
    reset_password,
    trucks_list,
    RoleBasedLoginView,
    add_booking,
    payment,
    admin_dashboard,
    faq
)
from accounts.views import register, verify_otp, company_register
from config import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", home, name="home"),
    path("trucks/", trucks_list, name="trucks_list"),
    path("faq/", faq, name="faq"),
    # Redirect root-level profile to accounts customer profile (with edit capabilities)
    path("profile/", RedirectView.as_view(url="/accounts/customer-profile/", permanent=False), name="root_profile"),
    
    # Custom Admin Panel (replaces default Django admin)
    path("admin/", admin_dashboard, name="custom_admin"),
    path("bookings/admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    
    path("bookings/", include("bookings.urls")),
    path("accounts/", include("accounts.urls")),
    path("fleet/", include("fleet.urls")),
    path("pricing/", include("pricing.urls")),

    # Auth - Custom login
    path("login/", RoleBasedLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/", register, name="register"),
    path("forgot-password/", forgot_password, name="forgot_password"),
    path("reset-password/", reset_password, name="reset_password"),
    path("company-register/", company_register, name="company_register"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve static files from STATICFILES_DIRS for development
    from django.contrib.staticfiles import views
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', views.serve),
    ]
else:
    # In production, WhiteNoise serves static files automatically
    # No additional URL patterns needed - WhiteNoise handles /static/
    pass

