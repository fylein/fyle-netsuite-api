# Generated by Django 3.1.14 on 2023-11-28 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0037_lastexportdetail'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='allow_intercompany_vendors',
            field=models.BooleanField(default=False, help_text='Allow intercompany vendors'),
        ),
    ]