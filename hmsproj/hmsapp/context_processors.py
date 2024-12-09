def base_template(request):
    """Context processor to determine the base template based on user role."""
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctors').exists():
            base_template = 'doctor/base_doctor.html'
        elif request.user.groups.filter(name='Administrators').exists():
            base_template = 'hosp_admin/base_admin.html'
        else:
            base_template = 'staff/base_staff.html'
    else:
        base_template = 'staff/base_staff.html'
    
    return {'base_template': base_template} 