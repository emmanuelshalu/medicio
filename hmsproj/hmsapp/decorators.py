from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import UserActivity

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.groups.filter(name='Administrators').exists():
            return view_func(request, *args, **kwargs)
        return redirect('login')
    return _wrapped_view

def doctor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.groups.filter(name='Doctors').exists():
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return _wrapped_view

def staff_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.groups.filter(name='Staff').exists():
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Staff privileges required.')
        return redirect('login')
    return wrap

def track_activity(activity_type, description=None):
    """
    Decorator to track user activities
    
    Usage:
    @track_activity('CREATE', 'Created new appointment')
    def create_appointment(request):
        # view code
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            if request.user.is_authenticated:
                # Get IP address
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = request.META.get('REMOTE_ADDR')
                
                # Create activity log
                UserActivity.objects.create(
                    user=request.user,
                    activity_type=activity_type,
                    activity_description=description or f"{activity_type} action performed",
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            
            return response
        return wrapped_view
    return decorator