# Generated by Django 3.1.14 on 2022-12-20 07:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0021_auto_20221214_1613'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='is_skipped',
            field=models.BooleanField(default=False, help_text='Expense is skipped or not', null=True),
        ),
    ]
