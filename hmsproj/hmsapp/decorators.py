from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib import messages

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