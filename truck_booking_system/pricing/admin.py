from django.contrib import admin
from .models import LoadType, Subscription


@admin.register(LoadType)
class LoadTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_multiplier')
    search_fields = ('name',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('company', 'amount', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('company__company_name',)
