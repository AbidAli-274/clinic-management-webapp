from rest_framework import permissions
from django.core.exceptions import PermissionDenied

def is_receptionist(user):
    # Check if the user is authenticated and has the 'receptionist' role
    if not user.is_authenticated:
        return False
    return user.role == "receptionist"



class IsAdminPermission:
    """Custom permission to allow access only to users with the 'admin' role."""
    
    def has_permission(self, request, view):
        # Check if the user is authenticated and has an admin role
        if request.user.is_authenticated and request.user.role == 's_admin':
            return True
        raise PermissionDenied("You do not have permission to create a user profile.")
