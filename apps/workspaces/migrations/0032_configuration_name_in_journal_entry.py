# Generated by Django 3.1.14 on 2023-06-16 09:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0031_configuration_import_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='name_in_journal_entry',
            field=models.CharField(choices=[('MERCHANT', 'MERCHANT'), ('EMPLOYEE', 'EMPLOYEE')], default='MERCHANT', help_text='Name in jounral entry for ccc expense only', max_length=100),
        ),
    ]
