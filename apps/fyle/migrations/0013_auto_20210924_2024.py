# Generated by Django 3.0.3 on 2021-09-24 20:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0012_expensegroup_response_logs'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='tax_amount',
            field=models.FloatField(help_text='Tax Amount', null=True),
        ),
        migrations.AddField(
            model_name='expense',
            name='tax_group_id',
            field=models.CharField(help_text='Tax Group ID', max_length=255, null=True),
        ),
    ]