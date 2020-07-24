# Generated by Django 3.0.3 on 2020-07-22 16:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fyle', '0002_expensegroup_fund_source'),
        ('netsuite', '0002_expensereport_expensereportlineitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='JournalEntry',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('currency', models.CharField(help_text='Journal Entry Currency', max_length=255)),
                ('subsidiary_id', models.CharField(help_text='NetSuite Subsidiary ID', max_length=255)),
                ('memo', models.CharField(help_text='Journal Entry Memo', max_length=255)),
                ('external_id', models.CharField(help_text='Journal Entry External ID', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Updated at')),
                ('expense_group', models.OneToOneField(help_text='Expense group reference', on_delete=django.db.models.deletion.PROTECT, to='fyle.ExpenseGroup')),
            ],
            options={
                'db_table': 'journal_entries',
            },
        ),
        migrations.CreateModel(
            name='JournalEntryLineItem',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('debit_account_id', models.CharField(help_text='NetSuite Debit account id', max_length=255)),
                ('account_id', models.CharField(help_text='NetSuite account id', max_length=255)),
                ('department_id', models.CharField(help_text='NetSuite department id', max_length=255, null=True)),
                ('location_id', models.CharField(help_text='NetSuite location id', max_length=255, null=True)),
                ('class_id', models.CharField(help_text='NetSuite class id', max_length=255, null=True)),
                ('entity_id', models.CharField(help_text='NetSuite entity id', max_length=255)),
                ('amount', models.FloatField(help_text='JournalEntry amount')),
                ('memo', models.CharField(help_text='NetSuite JournalEntry lineitem description', max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Updated at')),
                ('expense', models.OneToOneField(help_text='Reference to Expense', on_delete=django.db.models.deletion.PROTECT, to='fyle.Expense')),
                ('journal_entry', models.ForeignKey(help_text='Reference to JournalEntry', on_delete=django.db.models.deletion.PROTECT, to='netsuite.JournalEntry')),
            ],
            options={
                'db_table': 'journal_entry_lineitems',
            },
        ),
    ]
