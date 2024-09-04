# Generated by Django 3.2.14 on 2024-09-02 16:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netsuite', '0025_auto_20240229_0804'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='is_retired',
            field=models.BooleanField(default=False, help_text='Is Payment sync retried'),
        ),
        migrations.AddField(
            model_name='expensereport',
            name='is_retired',
            field=models.BooleanField(default=False, help_text='Is Payment sync retried'),
        ),
    ]
