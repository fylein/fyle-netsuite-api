# Generated by Django 3.0.3 on 2021-01-13 05:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mappings', '0004_auto_20201125_1643'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalmapping',
            name='location_level',
            field=models.CharField(help_text='Transaction Body, Line, Both', max_length=255, null=True),
        ),
    ]
