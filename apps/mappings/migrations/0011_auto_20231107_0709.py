# Generated by Django 3.1.14 on 2023-11-07 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mappings', '0010_auto_20231025_0915'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalmapping',
            name='department_level_id',
            field=models.CharField(help_text='NetSuite Department id', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='generalmapping',
            name='department_name',
            field=models.CharField(help_text='NetSuite Department name', max_length=255, null=True),
        ),
    ]
