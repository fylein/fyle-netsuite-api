# Generated by Django 3.2.14 on 2024-12-18 05:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0040_alter_configuration_change_accounting_period'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='is_attachment_upload_enabled',
            field=models.BooleanField(default=True, help_text='Is Attachment upload enabled'),
        ),
    ]