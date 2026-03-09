from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.company_dashboard, name='company_dashboard'),
    path('pending/', views.company_pending, name='company_pending'),
    path('trucks/', views.list_trucks, name='list_trucks'),
    path('drivers/', views.list_drivers, name='list_drivers'),
    path('add-truck/', views.add_truck, name='add_truck'),
    path('edit-truck/<int:truck_id>/', views.edit_truck, name='edit_truck'),
    path('delete-truck/<int:truck_id>/', views.delete_truck, name='delete_truck'),
    path('add-driver/', views.add_driver, name='add_driver'),
    path('edit-driver/<int:driver_id>/', views.edit_driver, name='edit_driver'),
    path('delete-driver/<int:driver_id>/', views.delete_driver, name='delete_driver'),
    # Booking management
    path('bookings/', views.company_bookings, name='company_bookings'),
    path('booking/<int:booking_id>/', views.company_booking_detail, name='company_booking_detail'),
    path('booking/<int:booking_id>/assign-driver/', views.assign_driver_to_booking, name='assign_driver_to_booking'),
]

