# Generated by Django 5.1.3 on 2024-12-14 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hmsapp', '0010_alter_payment_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='age',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]