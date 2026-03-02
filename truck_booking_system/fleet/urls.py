from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.company_dashboard, name='company_dashboard'),
    path('pending/', views.company_pending, name='company_pending'),
    path('add-truck/', views.add_truck, name='add_truck'),
    path('edit-truck/<int:truck_id>/', views.edit_truck, name='edit_truck'),
    path('delete-truck/<int:truck_id>/', views.delete_truck, name='delete_truck'),
]
