# Generated by Django 3.2.14 on 2024-02-29 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mappings', '0012_generalmapping_override_tax_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalmapping',
            name='class_id',
            field=models.CharField(help_text='NetSuite Class id', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='generalmapping',
            name='class_level',
            field=models.CharField(help_text='Transaction Body, Line, Both', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='generalmapping',
            name='class_name',
            field=models.CharField(help_text='NetSuite Class name', max_length=255, null=True),
        ),
    ]
