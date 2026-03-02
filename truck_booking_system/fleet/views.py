from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Company, Truck, Driver


@login_required
def company_dashboard(request):
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    if not company.is_approved:
        return redirect('company_pending')

    # Get company trucks
    trucks = Truck.objects.filter(company=company)
    
    # Get company drivers
    drivers = Driver.objects.filter(company=company)
    
    context = {
        'company': company,
        'trucks': trucks,
        'drivers': drivers,
    }
    return render(request, 'fleet/company_dashboard.html', context)


@login_required
def company_pending(request):
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return redirect('login')
    
    if company.is_approved:
        return redirect('company_dashboard')
    
    return render(request, 'fleet/company_pending.html', {'company': company})


@login_required
def add_truck(request):
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to add trucks.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    if not company.is_approved:
        messages.error(request, "Your company is not approved yet.")
        return redirect('company_pending')

    if request.method == 'POST':
        truck_number = request.POST.get('truck_number')
        truck_type = request.POST.get('truck_type')
        capacity = request.POST.get('capacity')
        price_per_km = request.POST.get('price_per_km')
        image = request.FILES.get('image')

        truck = Truck.objects.create(
            company=company,
            truck_number=truck_number,
            truck_type=truck_type,
            capacity=capacity,
            price_per_km=price_per_km,
            image=image,
            is_available=True
        )
        messages.success(request, "Truck added successfully!")
        return redirect('company_dashboard')

    truck_types = Truck.TRUCK_TYPES
    return render(request, 'fleet/add_truck.html', {'truck_types': truck_types})


@login_required
def edit_truck(request, truck_id):
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to edit trucks.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    truck = get_object_or_404(Truck, id=truck_id, company=company)

    if request.method == 'POST':
        truck.truck_number = request.POST.get('truck_number')
        truck.truck_type = request.POST.get('truck_type')
        truck.capacity = request.POST.get('capacity')
        truck.price_per_km = request.POST.get('price_per_km')
        if request.FILES.get('image'):
            truck.image = request.FILES.get('image')
        truck.save()
        messages.success(request, "Truck updated successfully!")
        return redirect('company_dashboard')

    truck_types = Truck.TRUCK_TYPES
    return render(request, 'fleet/edit_truck.html', {'truck': truck, 'truck_types': truck_types})


@login_required
def delete_truck(request, truck_id):
    if request.user.role != 'COMPANY':
        messages.error(request, "You are not authorized to delete trucks.")
        return redirect('login')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, "Company profile not found.")
        return redirect('login')

    truck = get_object_or_404(Truck, id=truck_id, company=company)
    truck.delete()
    messages.success(request, "Truck deleted successfully!")
    return redirect('company_dashboard')
