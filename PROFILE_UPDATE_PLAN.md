# Profile Update - One by One Implementation Plan

## Task
Allow users to update profile fields individually (photo, name, etc.) instead of all at once.

---

## Information Gathered

### Current Profile Templates:
1. **Customer Profile** (`accounts/templates/accounts/customer_profile.html`)
   - Single form with all fields
   - Fields: first_name, last_name, email, phone, address, date_of_birth, gender, profile_picture, password
   
2. **Driver Profile** (`accounts/templates/accounts/driver_profile.html`)
   - Single form with all fields
   - Fields: user fields + driver-specific (license_number, license_expiry, driver_phone, experience_years, driver_photo)
   
3. **Company Profile** (`accounts/templates/accounts/company_profile.html`)
   - Single form with all fields
   - Fields: company_name, trade_license, phone, address, website, contact_person, description, logo

### Current Views:
- `customer_profile()` - handles all customer profile updates
- `driver_profile_update()` - handles all driver profile updates  
- `company_profile_update()` - handles all company profile updates

---

## Plan

### Phase 1: Customer Profile Updates

#### Template Changes (`customer_profile.html`):
1. **Profile Photo Section** - Separate form with AJAX upload
   - Input: file upload for profile_picture
   - Save button for this section only
   
2. **Personal Information Section** - Separate form
   - Inputs: first_name, last_name
   - Save button for this section only
   
3. **Contact Information Section** - Separate form
   - Inputs: email, phone, address
   - Save button for this section only
   
4. **Additional Details Section** - Separate form
   - Inputs: date_of_birth, gender
   - Save button for this section only
   
5. **Change Password Section** - Separate form
   - Inputs: current_password, new_password, confirm_password
   - Save button for this section only

#### View Changes (`accounts/views.py`):
- Modify `customer_profile()` to handle individual field updates via AJAX
- Each form submission will update only specific fields

### Phase 2: Driver Profile Updates

#### Template Changes (`driver_profile.html`):
1. **User Profile Photo Section** - Separate form
2. **Driver Photo Section** - Separate form  
3. **Personal Information Section** - Separate form
4. **Driver Details Section** - Separate form (license_number, license_expiry, etc.)
5. **Additional Details Section** - Separate form

#### View Changes (`accounts/views.py`):
- Modify `driver_profile_update()` to handle individual field updates

### Phase 3: Company Profile Updates

#### Template Changes (`company_profile.html`):
1. **Company Logo Section** - Separate form
2. **Company Information Section** - Separate form
3. **Admin Contact Section** - Separate form

#### View Changes (`accounts/views.py`):
- Modify `company_profile_update()` to handle individual field updates

---

## Implementation Details

### Template Pattern:
```html
<!-- Each section is a separate form -->
<div class="info-section">
    <h4>Section Title</h4>
    <form method="POST" enctype="multipart/form-data" class="profile-update-form" data-section="field_name">
        {% csrf_token %}
        <!-- Fields here -->
        <button type="submit" class="btn-save">Save</button>
    </form>
    <div class="alert messages"></div>
</div>
```

### JavaScript:
- Add AJAX handlers for form submissions
- Show success/error messages per section
- Use Django's CSRF token for authentication

---

## Dependent Files to Edit

1. `truck_booking_system/accounts/templates/accounts/customer_profile.html`
2. `truck_booking_system/accounts/templates/accounts/driver_profile.html`
3. `truck_booking_system/accounts/templates/accounts/company_profile.html`
4. `truck_booking_system/accounts/views.py`

---

## Followup Steps
1. Test each profile type (customer, driver, company)
2. Verify AJAX submissions work correctly
3. Test error handling for each section
4. Verify profile pictures are uploaded correctly

---

## Status: PENDING USER APPROVAL

