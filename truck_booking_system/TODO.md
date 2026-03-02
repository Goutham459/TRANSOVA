# TODO - Company Registration & Approval System

## Completed Tasks
- [x] Plan confirmed by user
- [x] 1. Updated admin_dashboard view to include pending companies count
- [x] 2. Added pending companies badge in admin sidebar (via context processor)
- [x] 3. Added email notifications in admin_company_approve view
- [x] 4. Added email notifications in admin_company_disapprove view
- [x] 5. Added status check API endpoint for companies
- [x] 6. Updated company_pending template with auto-refresh JavaScript

## Summary of Changes Made:

### 1. bookings/views.py
- Added `pending_companies` count to admin_dashboard context
- Added email notification when admin approves company
- Added email notification when admin disapproves company
- Added `company_status_check` API endpoint for companies to check their approval status

### 2. bookings/urls.py
- Added import for `company_status_check`
- Added URL pattern for `/bookings/api/company/status/`

### 3. bookings/context_processors.py (NEW)
- Created context processor to automatically add `pending_companies` count to all admin templates

### 4. config/settings.py
- Added `bookings.context_processors.pending_companies_count` to template context processors

### 5. bookings/templates/bookings/admin_base.html
- Added pending companies badge with count in sidebar

### 6. fleet/templates/fleet/company_pending.html
- Added JavaScript to auto-check approval status every 10 seconds
- Shows success message and redirects to dashboard when approved

## Flow Summary:
1. Company registers → User created with role='COMPANY' + Company profile with is_approved=False
2. Company sees "Registration Pending" page with auto-refresh
3. Admin sees pending companies count in sidebar badge
4. Admin approves/disapproves company → email sent to company
5. Company page auto-refreshes and shows success when approved
6. Company can login and access dashboard
