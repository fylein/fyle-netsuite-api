# Generated by Django 4.2.20 on 2025-04-23 17:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0044_remove_configuration_is_simplify_report_closure_enabled_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='skip_accounting_export_summary_post',
            field=models.BooleanField(default=False, help_text='Skip accounting export summary post'),
        ),
    ]
