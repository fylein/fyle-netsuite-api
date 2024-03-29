# Generated by Django 3.2.14 on 2024-02-29 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netsuite', '0024_bill_override_tax_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='class_id',
            field=models.CharField(help_text='NetSuite Class id', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='creditcardcharge',
            name='class_id',
            field=models.CharField(help_text='NetSuite Class id', max_length=255, null=True),
        ),
    ]
