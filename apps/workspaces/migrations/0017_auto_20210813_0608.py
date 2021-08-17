# Generated by Django 3.0.3 on 2021-08-13 06:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0016_configuration_employee_field_mapping'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuration',
            name='employee_field_mapping',
            field=models.CharField(choices=[('EMPLOYEE', 'EMPLOYEE'), ('VENDOR', 'VENDOR')], help_text='Employee field mapping', max_length=50),
        ),
    ]
