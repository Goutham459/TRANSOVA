from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'pickup_location', 'drop_location', 'booking_date', 'truck', 'price', 'created_at')
    list_filter = ('booking_date', 'truck__truck_type')
    search_fields = ('customer_name', 'pickup_location', 'drop_location')
    date_hierarchy = 'booking_date'
    readonly_fields = ('created_at',)
