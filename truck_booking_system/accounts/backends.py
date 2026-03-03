from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class UsernameBackend(ModelBackend):
    """
    Custom authentication backend that supports both username and email login.
    Prioritizes username first, then falls back to email.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
            
        try:
            # Try to find user by username first
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # If not found by username, try email
            try:
                user = User.objects.get(email__iexact=username)
            except User.DoesNotExist:
                # Run the default password hasher once to reduce timing attacks
                User().set_password(password)
                return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
    
    def user_can_authenticate(self, user):
        """Check if the user is allowed to authenticate."""
        is_active = getattr(user, 'is_active', None)
        status = user.is_active if is_active is not None else True
        return status or user.is_superuser
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
        return user if self.user_can_authenticate(user) else None
