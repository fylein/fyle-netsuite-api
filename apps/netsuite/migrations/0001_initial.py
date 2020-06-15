# Generated by Django 3.0.3 on 2020-06-11 16:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('fyle', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('vendor_id', models.CharField(help_text='NetSuite vendor id', max_length=255)),
                ('subsidiary_id', models.CharField(help_text='NetSuite subsidiary id', max_length=255)),
                ('location_id', models.CharField(help_text='NetSuite Location id', max_length=255)),
                ('currency', models.CharField(help_text='Bill Currency', max_length=255)),
                ('memo', models.TextField(help_text='Bill Description')),
                ('external_id', models.CharField(help_text='Fyle reimbursement id', max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Updated at')),
                ('expense_group', models.OneToOneField(help_text='Expense group reference', on_delete=django.db.models.deletion.PROTECT, to='fyle.ExpenseGroup')),
            ],
            options={
                'db_table': 'bills',
            },
        ),
        migrations.CreateModel(
            name='BillLineitem',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('account_id', models.CharField(help_text='NetSuite account id', max_length=255)),
                ('location_id', models.CharField(help_text='NetSuite location id', max_length=255)),
                ('department_id', models.CharField(help_text='NetSuite department id', max_length=255)),
                ('amount', models.FloatField(help_text='Bill amount')),
                ('memo', models.CharField(help_text='NetSuite bill lineitem memo', max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Updated at')),
                ('bill', models.ForeignKey(help_text='Reference to bill', on_delete=django.db.models.deletion.PROTECT, to='netsuite.Bill')),
                ('expense', models.OneToOneField(help_text='Reference to Expense', on_delete=django.db.models.deletion.PROTECT, to='fyle.Expense')),
            ],
            options={
                'db_table': 'bill_lineitems',
            },
        ),
    ]
