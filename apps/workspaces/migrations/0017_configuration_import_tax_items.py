# Generated by Django 3.0.3 on 2021-09-15 09:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0016_configuration_employee_field_mapping'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='import_tax_items',
            field=models.BooleanField(default=False, help_text='Auto import tax items to Fyle'),
        ),
    ]
