from django.contrib import admin
from django.utils.html import format_html

from .models import Bid, Booking, FAQQuestion, Payment, ProofOfDelivery


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "pickup_location",
        "drop_location",
        "booking_date",
        "truck",
        "price",
        "created_at",
    )
    list_filter = ("booking_date", "truck__truck_type", "payment_status", "status")
    search_fields = ("customer_name", "pickup_location", "drop_location", "id")
    date_hierarchy = "booking_date"
    readonly_fields = ("created_at",)
