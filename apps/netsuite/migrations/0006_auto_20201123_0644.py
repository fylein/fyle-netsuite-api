# Generated by Django 3.0.3 on 2020-11-23 06:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0006_reimbursement'),
        ('netsuite', '0005_auto_20201027_0930'),
    ]

    operations = [
        migrations.CreateModel(
            name='VendorPaymentLineitem',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('doc_id', models.CharField(help_text='NetSuite Object id', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Updated at')),
            ],
            options={
                'db_table': 'vendor_payment_lineitems',
            },
        ),
        migrations.AddField(
            model_name='bill',
            name='payment_synced',
            field=models.BooleanField(default=False, help_text='Payment synced status'),
        ),
        migrations.AddField(
            model_name='expensereport',
            name='payment_synced',
            field=models.BooleanField(default=False, help_text='Payment synced status'),
        ),
        migrations.AddField(
            model_name='journalentry',
            name='payment_synced',
            field=models.BooleanField(default=False, help_text='Payment synced status'),
        ),
        migrations.AlterField(
            model_name='billlineitem',
            name='memo',
            field=models.TextField(help_text='NetSuite bill lineitem memo', null=True),
        ),
        migrations.AlterField(
            model_name='expensereport',
            name='memo',
            field=models.TextField(help_text='Expense Report Description'),
        ),
        migrations.AlterField(
            model_name='expensereportlineitem',
            name='memo',
            field=models.TextField(help_text='NetSuite ExpenseReport lineitem memo', null=True),
        ),
        migrations.AlterField(
            model_name='journalentrylineitem',
            name='memo',
            field=models.TextField(help_text='NetSuite JournalEntry lineitem description', null=True),
        ),
        migrations.CreateModel(
            name='VendorPayment',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('accounts_payable_id', models.CharField(help_text='NetSuite Accounts Payable Account id', max_length=255, null=True)),
                ('account_id', models.CharField(help_text='NetSuite Account id', max_length=255, null=True)),
                ('entity_id', models.CharField(help_text='NetSuite entity id ( Vendor / Employee )', max_length=255)),
                ('currency', models.CharField(help_text='Vendor Payment Currency', max_length=255)),
                ('department_id', models.CharField(help_text='NetSuite Department id', max_length=255, null=True)),
                ('location_id', models.CharField(help_text='NetSuite Location id', max_length=255, null=True)),
                ('class_id', models.CharField(help_text='NetSuite Class id', max_length=255, null=True)),
                ('subsidiary_id', models.CharField(help_text='NetSuite subsidiary id', max_length=255)),
                ('external_id', models.CharField(help_text='Fyle settlement id', max_length=255, unique=True)),
                ('memo', models.TextField(help_text='Vendor Payment Description', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Updated at')),
                ('expense_group', models.OneToOneField(help_text='Expense group reference', on_delete=django.db.models.deletion.PROTECT, to='fyle.ExpenseGroup')),
            ],
            options={
                'db_table': 'vendor_payments',
            },
        ),
    ]
