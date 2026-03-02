from django.contrib import admin
from .models import Company, Truck, Driver


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('company_name', 'user__email')
    actions = ['approve_companies']

    def approve_companies(self, request, queryset):
        queryset.update(is_approved=True)


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ('truck_number', 'truck_type', 'capacity', 'is_available', 'price_per_km', 'company')
    list_filter = ('truck_type', 'is_available', 'company')
    search_fields = ('truck_number',)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'company')
    list_filter = ('company',)
    search_fields = ('user__username', 'user__email')
