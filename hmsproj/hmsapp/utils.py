from functools import wraps
from django.shortcuts import redirect

def admin_required(view_func):
    """Decorator to restrict access to admin users only"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.roles.filter(name__in=['SUPER_ADMIN', 'ADMIN']).exists():
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return _wrapped_view

def doctor_required(view_func):
    """Decorator to restrict access to doctors only"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.roles.filter(name='DOCTOR').exists():
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return _wrapped_view 