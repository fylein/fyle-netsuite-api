# Generated by Django 3.0.3 on 2020-07-03 06:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mappings', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generalmapping',
            name='location_id',
            field=models.CharField(help_text='NetSuite Location id', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='generalmapping',
            name='location_name',
            field=models.CharField(help_text='NetSuite Location name', max_length=255, null=True),
        ),
    ]
