# Generated by Django 3.0.3 on 2021-10-01 04:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0018_workspace_cluster_domain'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='change_accounting_period',
            field=models.BooleanField(default=False, help_text='Change the accounting period'),
        ),
    ]
