# Generated by Django 3.0.3 on 2020-10-13 15:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0004_auto_20201007_0838'),
    ]

    operations = [
        migrations.AddField(
            model_name='expensegroup',
            name='exported_at',
            field=models.DateTimeField(help_text='Exported at', null=True),
        ),
    ]
