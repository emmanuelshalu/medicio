# Hospital Management System (HMS) Project Documentation

## Project Setup and Environment

1. **Virtual Environment Setup**
   - Created a virtual environment using `python -m venv hmsenv`
   - Activated the virtual environment
   - Installed required dependencies using pip

2. **Django Project Initialization**
   - Created Django project using `django-admin startproject hmsproj`
   - Created main application using `python manage.py startapp hmsapp`
   - Added 'hmsapp' to INSTALLED_APPS in settings.py

3. **Dependencies Installation**
   Key packages installed:
   - Django 5.1.3
   - Pillow for image handling
   - django-crispy-forms with crispy-bootstrap5
   - Google Calendar API packages
   - QR Code generation package
   - Python-dotenv for environment variables

## Database Models

1. **User Management Models**
   - Extended Django's User model
   - Created specialized profiles:
     - DoctorProfile
     - StaffProfile
     - Patient

2. **Appointment System Models**
   - Appointment model with status tracking
   - DoctorAvailability for scheduling
   - Treatment records
   - Medical records management

3. **Additional Models**
   - Specialty model for doctor categorization
   - Custom validators for phone numbers and file uploads
   - Integration with Google Calendar

## Views and Features

1. **Authentication System**
   - Custom login view with role-based redirection
   - User role management (Admin, Doctor, Staff)
   - Decorators for role-based access control

2. **Appointment Management**
   - Appointment booking system
   - Availability checking
   - Schedule management
   - Google Calendar integration
                                        - QR code generation for appointments

3. **Patient Management**
   - Patient registration
   - Medical history tracking
   - Treatment records
   - File upload for medical records

4. **Doctor Management**
   - Doctor profile management
   - Availability settings
   - Schedule viewing
   - Treatment recording

5. **Staff Features**
   - Patient registration
   - Appointment management
   - Basic record keeping

6. **Admin Features**
   - User management
   - System monitoring
   - Reports generation
   - Settings management

## Security Features

1. **Authentication and Authorization**
   - Role-based access control
   - Custom decorators for view protection
                                            - Secure password handling

2. **Data Protection**
                                            - File upload validation
                                            - Secure storage of sensitive information
   - Input validation and sanitization

## Frontend Development

1. **Templates**
   - Bootstrap-based responsive design
   - Custom forms using crispy-forms
   - Dynamic content loading
                            - Interactive scheduling interface

2. **Static Files**
   - CSS customization
                                - JavaScript for dynamic features
   - Image assets management

## API Integrations

1. **Google Calendar**
   - OAuth2 authentication
                                    - Event creation and management
                                    - Synchronization with appointments

## Deployment

1. **Local Development**
   - Debug settings
   - Development server configuration
   - Static files handling

2. **Production Deployment**
   - Python Anywhere hosting
   - Static files configuration
   - Database migration
   - Environment variables setup

## Version Control

1. **Git Repository**
   - Initial repository setup
   - Branch management
   - Commit history
   - .gitignore configuration

## Additional Features

1. **Reporting System**
   - Appointment statistics
   - Patient demographics
   - Treatment summaries
   - Financial reports

2. **Notification System**
                            - Appointment reminders
                            - Status updates
                            - Email notifications

3. **File Management**
   - Medical records upload
   - Document storage
   - File type validation

## Future Enhancements

1. **Planned Features**
   - Mobile application integration
   - Advanced reporting
   - Telemedicine support
   - Payment gateway integration

## Testing

1. **Testing Framework**
   - Unit tests setup
   - Integration testing
   - User acceptance testing

## Documentation

1. **Code Documentation**
   - Docstrings
   - Comments
   - README files
   - API documentation
