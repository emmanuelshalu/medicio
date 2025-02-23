# Generated by Django 5.1.3 on 2024-12-09 19:41

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hmsapp', '0007_loginactivity_useractivity'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('report_type', models.CharField(choices=[('PATIENT_DEMOGRAPHICS', 'Patient Demographics'), ('REVENUE_ANALYSIS', 'Revenue Analysis'), ('APPOINTMENT_TRENDS', 'Appointment Trends'), ('SERVICE_UTILIZATION', 'Service Utilization'), ('DOCTOR_PERFORMANCE', 'Doctor Performance')], max_length=50)),
                ('frequency', models.CharField(choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly'), ('QUARTERLY', 'Quarterly'), ('YEARLY', 'Yearly')], max_length=20)),
                ('filters', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
