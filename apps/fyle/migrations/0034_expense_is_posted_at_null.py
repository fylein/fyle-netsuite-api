# Generated by Django 3.2.14 on 2024-11-17 20:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0033_expense_paid_on_fyle'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='is_posted_at_null',
            field=models.BooleanField(default=False, help_text='Flag check if posted at is null or not'),
        ),
    ]