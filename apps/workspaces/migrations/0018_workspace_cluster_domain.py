# Generated by Django 3.0.3 on 2021-09-24 09:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0017_configuration_import_tax_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='cluster_domain',
            field=models.CharField(help_text='Fyle Cluster Domain', max_length=255, null=True),
        ),
    ]
