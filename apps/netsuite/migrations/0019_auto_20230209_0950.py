# Generated by Django 3.1.14 on 2023-02-09 09:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netsuite', '0018_auto_20220301_1300'),
    ]

    operations = [
        migrations.AddField(
            model_name='billlineitem',
            name='netsuite_receipt_url',
            field=models.TextField(help_text='NetSuite Receipt URL', null=True),
        ),
        migrations.AddField(
            model_name='expensereportlineitem',
            name='netsuite_receipt_url',
            field=models.TextField(help_text='NetSuite Receipt URL', null=True),
        ),
        migrations.AddField(
            model_name='journalentrylineitem',
            name='netsuite_receipt_url',
            field=models.TextField(help_text='NetSuite Receipt URL', null=True),
        ),
    ]
