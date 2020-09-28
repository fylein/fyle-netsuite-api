# Generated by Django 3.0.3 on 2020-09-24 15:48

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('netsuite', '0002_expensereports_journalentries'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='transaction_date',
            field=models.DateField(default=django.utils.timezone.now, help_text='Bill transaction date'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='expensereport',
            name='transaction_date',
            field=models.DateField(default=django.utils.timezone.now, help_text='Bill transaction date'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='journalentry',
            name='transaction_date',
            field=models.DateField(default=django.utils.timezone.now, help_text='Bill transaction date'),
            preserve_default=False,
        ),
    ]
