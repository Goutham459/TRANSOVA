from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    home, add_booking, booking_list, edit_booking, delete_booking, 
    dashboard, customer_booking, payment, payment_success, payment_cancel,
    customer_dashboard, admin_dashboard, driver_dashboard,
    # Driver views
    driver_profile, driver_jobs, driver_update_job_status, driver_accept_job, driver_reject_job,
    driver_delivery_proof,
    # Admin views
    admin_users, admin_user_detail, admin_user_delete,
    admin_trucks, admin_truck_add, admin_truck_edit, admin_truck_delete,
    admin_companies, admin_company_approve, admin_company_disapprove,
    admin_drivers,
    admin_load_types, admin_load_type_add, admin_load_type_edit, admin_load_type_delete,
    admin_subscriptions, admin_subscription_toggle,
    admin_stats,
    company_status_check,
    # User management
    admin_user_toggle_status, admin_user_change_role, admin_reset_password,
    # FAQ views
    faq, faq_submit, faq_reply, admin_faq, admin_faq_toggle_public,
    # New customer features
    profile, booking_receipt, customer_booking_list,
    # Payment
    process_payment,
    download_receipt_pdf
)

urlpatterns = [
    path("", home, name="home"),
    path("list/", booking_list, name="booking_list"),
    path("add/", add_booking, name="add_booking"),
    path("edit/<int:booking_id>/", edit_booking, name="edit_booking"),
    path("delete/<int:booking_id>/", delete_booking, name="delete_booking"),
    path("dashboard/", dashboard, name="dashboard"),
    path("customer-dashboard/", customer_dashboard, name="customer_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("driver-dashboard/", driver_dashboard, name="driver_dashboard"),
    path("driver-jobs/", driver_jobs, name="driver_jobs"),
    path("driver-profile/", driver_profile, name="driver_profile"),
    path("driver/job/<int:booking_id>/<str:new_status>/", driver_update_job_status, name="driver_update_job_status"),
    path("driver/job/<int:booking_id>/accept/", driver_accept_job, name="driver_accept_job"),
    path("driver/job/<int:booking_id>/reject/", driver_reject_job, name="driver_reject_job"),
    path("driver/job/<int:booking_id>/proof/", driver_delivery_proof, name="driver_delivery_proof"),
    path("book/", customer_booking, name="customer_booking"),
    path("payment/", payment, name="payment"),
    path("payment/success/", payment_success, name="payment_success"),
    path("payment/cancel/", payment_cancel, name="payment_cancel"),
    
    
    # Custom Admin URLs
    path("admin/users/", admin_users, name="admin_users"),
    path("admin/users/<int:user_id>/", admin_user_detail, name="admin_user_detail"),
    path("admin/users/<int:user_id>/delete/", admin_user_delete, name="admin_user_delete"),
    path("admin/trucks/", admin_trucks, name="admin_trucks"),
    path("admin/trucks/add/", admin_truck_add, name="admin_truck_add"),
    path("admin/trucks/<int:truck_id>/edit/", admin_truck_edit, name="admin_truck_edit"),
    path("admin/trucks/<int:truck_id>/delete/", admin_truck_delete, name="admin_truck_delete"),
    path("admin/companies/", admin_companies, name="admin_companies"),
    path("admin/companies/<int:company_id>/approve/", admin_company_approve, name="admin_company_approve"),
    path("admin/companies/<int:company_id>/disapprove/", admin_company_disapprove, name="admin_company_disapprove"),
    path("admin/drivers/", admin_drivers, name="admin_drivers"),
    path("admin/load-types/", admin_load_types, name="admin_load_types"),
    path("admin/load-types/add/", admin_load_type_add, name="admin_load_type_add"),
    path("admin/load-types/<int:load_type_id>/edit/", admin_load_type_edit, name="admin_load_type_edit"),
    path("admin/load-types/<int:load_type_id>/delete/", admin_load_type_delete, name="admin_load_type_delete"),
    path("admin/subscriptions/", admin_subscriptions, name="admin_subscriptions"),
    path("admin/subscriptions/<int:subscription_id>/toggle/", admin_subscription_toggle, name="admin_subscription_toggle"),
    path("admin/stats/", admin_stats, name="admin_stats"),
    path("admin/faq/", admin_faq, name="admin_faq"),
    
    # User management URLs
    path("admin/users/<int:user_id>/toggle-status/", admin_user_toggle_status, name="admin_user_toggle_status"),
    path("admin/users/<int:user_id>/change-role/", admin_user_change_role, name="admin_user_change_role"),
    path("admin/users/<int:user_id>/reset-password/", admin_reset_password, name="admin_reset_password"),
    
    # Company status check API
    path("api/company/status/", company_status_check, name="company_status_check"),
    
    # FAQ URLs
    path("faq/", faq, name="faq"),
    path("faq/submit/", faq_submit, name="faq_submit"),
    path("faq/<int:question_id>/reply/", faq_reply, name="faq_reply"),
    path("admin/faq/<int:question_id>/toggle-public/", admin_faq_toggle_public, name="admin_faq_toggle_public"),
    
    # New Customer Feature URLs
    path("profile/", profile, name="profile"),
    path("bookings/receipt/<int:booking_id>/", booking_receipt, name="booking_receipt"),
    path("bookings/receipt/<int:booking_id>/download/", download_receipt_pdf, name="download_receipt_pdf"),
    path("my-bookings/", customer_booking_list, name="customer_booking_list"),
    
    # Payment processing
    path("process-payment/", process_payment, name="process_payment"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

