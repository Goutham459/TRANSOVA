from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('company-register/', views.company_register, name='company_register'),
    path('company-pending/', views.company_pending, name='company_pending'),
    path("register/", views.register, name="register"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name='accounts/login.html'),
        name="login"
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page='/login/'),
        name="logout"
    ),
    # Profile URLs
    path('customer-profile/', views.customer_profile, name='customer_profile'),
    path('driver-profile/', views.driver_profile_update, name='driver_profile_update'),
    path('company-profile/', views.company_profile_update, name='company_profile_update'),
]
