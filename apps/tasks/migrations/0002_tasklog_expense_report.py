# Generated by Django 3.0.3 on 2020-07-20 08:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('netsuite', '0002_expensereport_expensereportlineitem'),
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tasklog',
            name='expense_report',
            field=models.ForeignKey(help_text='Reference to Expense Report', null=True, on_delete=django.db.models.deletion.PROTECT, to='netsuite.ExpenseReport'),
        ),
        migrations.AddField(
            model_name='tasklog',
            name='journal_entry',
            field=models.ForeignKey(help_text='Reference to journal_entry', null=True, on_delete=django.db.models.deletion.PROTECT, to='netsuite.JournalEntry'),
        ),
    ]
