# Generated by Django 3.1.14 on 2022-02-08 14:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0017_auto_20220119_0821'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='corporate_card_id',
            field=models.CharField(blank=True, help_text='Corporate Card ID', max_length=255, null=True),
        ),
    ]
