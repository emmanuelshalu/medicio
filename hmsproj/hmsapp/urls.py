from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Public Pages
    path('', views.home, name='home'),
    path('terms/', views.terms_conditions, name='terms_conditions'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('get-doctors/<int:specialty_id>/', views.get_doctors, name='get_doctors'),

    # Shared URLs
    path('hosp_admin/doctors/<int:doctor_id>/view/', views.view_doctor, name='view_doctor'),
    path('hosp_admin/patients/', views.manage_patients, name='manage_patients'),

    # Doctor URLs
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/profile/', views.doctor_profile, name='doctor_profile'),
    path('doctor/availability/', views.manage_availability, name='manage_availability'),
    path('doctor/google-calendar/auth/', views.google_calendar_auth, name='google_calendar_auth'),
    path('doctor/google-calendar/callback/', views.google_calendar_callback, name='google_calendar_callback'),
    path('doctor/google-calendar/disconnect/', views.google_calendar_disconnect, name='google_calendar_disconnect'),
    # path('doctor/patient/<str:patient_id>/', views.view_patient, name='view_patient'),
    # path('doctor/treatment/<int:appointment_id>/', views.add_treatment, name='add_treatment'),

    # Hospital Admin URLs
    path('hosp_admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('hosp_admin/doctors/', views.manage_doctors, name='manage_doctors'),

    path('hosp_admin/doctors/<int:doctor_id>/edit/', views.edit_doctor, name='edit_doctor'),
    path('hosp_admin/doctors/<int:doctor_id>/delete/', views.delete_doctor, name='delete_doctor'),

    # path('hosp_admin/patients/add/', views.add_patient, name='add_patient'),
    path('hosp_admin/patients/<int:patient_id>/view/', views.view_patient, name='view_patient'),
    path('hosp_admin/patients/<int:patient_id>/edit/', views.edit_patient, name='edit_patient'),
    path('hosp_admin/patients/<int:patient_id>/delete/', views.delete_patient, name='delete_patient'),
    path('hosp_admin/appointments/', views.manage_appointments, name='manage_appointments'),
    path('hosp_admin/appointments/<int:appointment_id>/view/', views.view_appointment, name='view_appointment'),
    path('hosp_admin/appointments/<int:appointment_id>/edit/', views.edit_appointment, name='edit_appointment'),
    path('hosp_admin/appointments/<int:appointment_id>/delete/', views.delete_appointment, name='delete_appointment'),
    path('hosp_admin/staff/', views.manage_staff, name='manage_staff'),
    path('hosp_admin/staff/<int:staff_id>/view/', views.view_staff, name='view_staff'),
    path('hosp_admin/staff/<int:staff_id>/edit/', views.edit_staff, name='edit_staff'),
    path('hosp_admin/staff/<int:staff_id>/delete/', views.delete_staff, name='delete_staff'),
    path('hosp_admin/bills/', views.manage_bills, name='manage_bills'),
    path('hosp_admin/bills/<int:bill_id>/view/', views.view_bill, name='view_bill'),
    path('hosp_admin/bills/<int:bill_id>/edit/', views.edit_bill, name='edit_bill'),
    path('hosp_admin/bills/create/', views.create_bill, name='create_bill'),
    path('hosp_admin/bills/<int:bill_id>/delete/', views.delete_bill, name='delete_bill'),
    path('hosp_admin/bills/<int:bill_id>/record-payment/', views.record_payment, name='record_payment'),
    path('hosp_admin/user-activities/', views.view_user_activities, name='view_user_activities'),
    path('hosp_admin/login-activities/', views.view_login_activities, name='view_login_activities'),

    # Staff URLs
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/treatments/', views.manage_treatments, name='manage_treatments'),
    path('staff/treatments/add/', views.add_treatment, name='add_treatment'),
    path('staff/treatments/<int:treatment_id>/edit/', views.edit_treatment, name='edit_treatment'),
    path('staff/treatments/<int:treatment_id>/delete/', views.delete_treatment, name='delete_treatment'),
    path('staff/treatments/<int:treatment_id>/view/', views.view_treatment, name='view_treatment'),
    path('staff/doctors/', views.all_doctors, name='all_doctors'),

    # Treatment URLs
    path('treatment/<int:treatment_id>/view/', views.view_treatment, name='view_treatment'),
    path('treatment/<int:treatment_id>/edit/', views.edit_treatment, name='edit_treatment'),
    path('treatment/<int:treatment_id>/delete/', views.delete_treatment, name='delete_treatment'),
    path('treatment/add/', views.add_treatment, name='add_treatment'),

    # API URLs
    path('api/find-next-slot/', views.find_next_slot, name='find_next_slot'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('bills/<int:bill_id>/', views.view_bill, name='view_bill'),
    path('bills/<int:bill_id>/upi-payment/', views.upi_payment, name='upi_payment'),
    path('bills/<int:bill_id>/verify-upi-payment/', views.verify_upi_payment, name='verify_upi_payment'),
] 

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)