from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

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