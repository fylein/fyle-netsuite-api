# Generated by Django 3.0.3 on 2020-12-21 07:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0004_workspacegeneralsettings_sync_payments'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='workspacegeneralsettings',
            table='general_settings',
        ),
        migrations.AlterModelTable(
            name='workspaceschedule',
            table='workspace_schedules',
        ),
    ]
