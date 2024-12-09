from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from .models import LoginActivity, UserActivity

class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                role = request.user.userprofile.role.name
                if request.path.startswith('/admin/'):
                    if role not in ['SUPER_ADMIN', 'ADMIN']:
                        messages.error(request, 'Access Denied: Insufficient privileges')
                        return redirect('home')
            except:
                pass
        return self.get_response(request) 

class ActivityTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed before the view
        response = self.get_response(request)
        
        # Code to be executed after the view
        if request.user.is_authenticated:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')

            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Update or create login activity
            if not hasattr(request, 'login_activity'):
                LoginActivity.objects.get_or_create(
                    user=request.user,
                    session_key=request.session.session_key,
                    defaults={
                        'ip_address': ip_address,
                        'user_agent': user_agent
                    }
                )

        return response 