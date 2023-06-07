# Generated by Django 3.1.14 on 2023-05-23 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netsuite', '0020_auto_20230216_0455'),
    ]

    operations = [
        migrations.AddField(
            model_name='billlineitem',
            name='detail_type',
            field=models.CharField(default='AccountBasedExpenseLineDetail', help_text='Detail type for the lineitem', max_length=255),
        ),
        migrations.AddField(
            model_name='billlineitem',
            name='item_id',
            field=models.CharField(help_text='Netsuite item id', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='billlineitem',
            name='account_id',
            field=models.CharField(help_text='NetSuite account id', max_length=255, null=True),
        ),
    ]