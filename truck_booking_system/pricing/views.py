from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from fleet.models import Company

from .models import Subscription


@login_required
def subscribe(request):
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return redirect("login")

    if request.method == "POST":
        amount = request.POST.get("amount", 199)
        days = int(request.POST.get("days", 30))

        Subscription.objects.create(
            company=company,
            amount=amount,
            end_date=date.today() + timedelta(days=days),
            is_active=True,
        )
        return redirect("company_dashboard")

    return render(request, "pricing/subscribe.html")


@login_required
def subscription_status(request):
    try:
        company = Company.objects.get(user=request.user)
        subscription = Subscription.objects.filter(
            company=company, is_active=True
        ).first()
    except Company.DoesNotExist:
        subscription = None

    return render(
        request, "pricing/subscription_status.html", {"subscription": subscription}
    )
