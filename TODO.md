# TODO: Fix Django ImportError - Remove Promo Functionality
## Detailed Steps from Approved Plan:

### 1. ✅ Create TODO.md (current) - Done

### 2. ✅ Clean bookings/views.py 
- Remove 'promos': promos from home() context ✓
- Update home() docstring: remove promo mentions ✓

### 3. ✅ Clean bookings/admin.py 
- Remove imports: PromoCode, PromoUsage ✓
- Delete @admin.register(PromoCode), PromoCodeAdmin class ✓
- Delete @admin.register(PromoUsage), PromoUsageAdmin class ✓ 
- In BookingAdmin: Remove 'promo_discount' from list_display ✓
- Delete promo_discount_display method ✓
- Remove 'promo_discount_display' from readonly_fields ✓

### 4. ✅ Check & clean fleet/views.py 
- No promo references found ✓

### 5. 🧪 Test: cd truck_booking_system && python manage.py runserver

### 6. ✅️ Verify core features 
- Customer booking, dashboard work
- Admin pages load without ImportError
- Home page renders

### 7. 🗑️ [Optional] Remove unused promo templates
- fleet/templates/fleet/company_promos_list.html
- fleet/templates/fleet/company_promo_form.html

**Progress: 4/7 → Ready for testing**
