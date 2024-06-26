# Generated by Django 3.2.14 on 2024-05-09 13:01

import apps.fyle.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0030_auto_20240208_1206'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expensegroupsettings',
            name='expense_state',
            field=models.CharField(default=apps.fyle.models.get_default_expense_state, help_text='state at which the expenses are fetched ( PAYMENT_PENDING / PAYMENT_PROCESSING / PAID)', max_length=100, null=True),
        ),
    ]
