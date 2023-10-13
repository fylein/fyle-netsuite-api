# Generated by Django 3.1.14 on 2023-10-12 07:50

import apps.workspaces.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0033_workspace_onboarding_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workspace',
            name='onboarding_state',
            field=models.CharField(choices=[('CONNECTION', 'CONNECTION'), ('SUBSIDIARY', 'SUBSIDIARY'), ('MAP_EMPLOYEES', 'MAP_EMPLOYEES'), ('EXPORT_SETTINGS', 'EXPORT_SETTINGS'), ('IMPORT_SETTINGS', 'IMPORT_SETTINGS'), ('ADVANCED_CONFIGURATION', 'ADVANCED_CONFIGURATION'), ('COMPLETE', 'COMPLETE')], default=apps.workspaces.models.get_default_onboarding_state, help_text='Onboarding status of the workspace', max_length=50, null=True),
        ),
    ]
