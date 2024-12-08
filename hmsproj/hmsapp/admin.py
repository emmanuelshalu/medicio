from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    Specialty, DoctorProfile, Patient, DoctorAvailability,
    Appointment, Treatment, Bill, StaffProfile, MedicalRecord
)

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('doctor_id', 'get_doctor_name', 'specialty', 'license_number', 'phone_number')
    list_filter = ('specialty', 'created_at')
    search_fields = ('doctor_id', 'user__first_name', 'user__last_name', 'license_number')
    readonly_fields = ('doctor_id', 'created_at', 'updated_at')

    def get_doctor_name(self, obj):
        return f"Dr. {obj.user.get_full_name()}"
    get_doctor_name.short_description = 'Doctor Name'

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'get_staff_name', 'department', 'designation', 'phone_number')
    list_filter = ('department', 'created_at')
    search_fields = ('staff_id', 'user__first_name', 'user__last_name')
    readonly_fields = ('staff_id', 'created_at', 'updated_at')

    def get_staff_name(self, obj):
        return obj.user.get_full_name()
    get_staff_name.short_description = 'Staff Name'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'get_doctor_name', 'appointment_date', 'appointment_time', 'status', 'has_medical_records')
    list_filter = ('status', 'appointment_date')
    search_fields = ('patient__patient_name', 'doctor__user__first_name', 'doctor__user__last_name')
    readonly_fields = ('created_at', 'updated_at')

    def get_patient_name(self, obj):
        return obj.patient.patient_name
    get_patient_name.short_description = 'Patient'

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"
    get_doctor_name.short_description = 'Doctor'

    def has_medical_records(self, obj):
        if obj.medical_records:
            return format_html('<a href="{}" target="_blank">View Records</a>', obj.medical_records.url)
        return "No Records"
    has_medical_records.short_description = 'Medical Records'

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'record_date', 'description', 'view_document', 'uploaded_at')
    list_filter = ('record_date', 'uploaded_at')
    search_fields = ('patient__patient_name', 'description')
    readonly_fields = ('uploaded_at',)
    ordering = ('-record_date', '-uploaded_at')

    def get_patient_name(self, obj):
        return obj.patient.patient_name
    get_patient_name.short_description = 'Patient'

    def view_document(self, obj):
        if obj.document:
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.document.url)
        return "No Document"
    view_document.short_description = 'Document'

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'patient_name', 'phone_number', 'blood_group', 'gender', 'view_medical_records')
    list_filter = ('blood_group', 'gender', 'created_at')
    search_fields = ('patient_id', 'patient_name', 'phone_number')
    readonly_fields = ('patient_id', 'created_at', 'updated_at')

    def view_medical_records(self, obj):
        records_count = MedicalRecord.objects.filter(patient=obj).count()
        if records_count > 0:
            return format_html(
                '<a href="/admin/hmsapp/medicalrecord/?patient__id__exact={}" target="_blank">{} Records</a>',
                obj.id,
                records_count
            )
        return "No Records"
    view_medical_records.short_description = 'Medical Records'

# Register other models
admin.site.register(Specialty)
admin.site.register(DoctorAvailability)
admin.site.register(Treatment)
admin.site.register(Bill)

