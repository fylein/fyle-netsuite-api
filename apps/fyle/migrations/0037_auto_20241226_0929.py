# Generated by Django 3.2.14 on 2024-12-26 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0036_expense_masked_corporate_card_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='expensegroupsettings',
            name='created_by',
            field=models.CharField(blank=True, help_text='Email of the user who created this record', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='expensegroupsettings',
            name='updated_by',
            field=models.CharField(blank=True, help_text='Email of the user who last updated this record', max_length=255, null=True),
        ),
    ]