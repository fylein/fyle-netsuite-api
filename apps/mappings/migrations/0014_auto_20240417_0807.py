# Generated by Django 3.2.14 on 2024-04-17 08:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mappings', '0013_auto_20240229_0804'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalmapping',
            name='default_tax_code_id',
            field=models.CharField(help_text='Netsuite default Tax Code ID', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='generalmapping',
            name='default_tax_code_name',
            field=models.CharField(help_text='Netsuite default Tax Code name', max_length=255, null=True),
        ),
    ]