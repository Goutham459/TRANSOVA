from django.urls import path
from . import views

urlpatterns = [
    path('subscribe/', views.subscribe, name='subscribe'),
    path('subscription-status/', views.subscription_status, name='subscription_status'),
]
