from fleet.models import Company

def pending_companies_count(request):
    """Context processor to add pending companies count to all templates"""
    try:
        # Only show for admin users
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser or request.user.role == 'ADMIN'):
            return {'pending_companies': Company.objects.filter(is_approved=False).count()}
    except:
        pass
    return {'pending_companies': 0}
